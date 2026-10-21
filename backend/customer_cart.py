from uuid import uuid4

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from customer_auth import customer_bearer, get_customer_profile
from pos import _request


class CartItemInput(BaseModel):
    product_id: str
    qty: int = Field(gt=0)


async def _cart(client: httpx.AsyncClient, customer_id: str) -> dict:
    rows = await _request(client, "GET", "carts", params={"customer_id": f"eq.{customer_id}", "select": "*"})
    if rows:
        return rows[0]
    rows = await _request(client, "POST", "carts", body={"cart_id": str(uuid4()), "customer_id": customer_id}, prefer="return=representation")
    return rows[0]


async def get_cart(credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    profile = await get_customer_profile(credentials)
    async with httpx.AsyncClient(timeout=10) as client:
        cart = await _cart(client, profile["customer_id"])
        items = await _request(client, "GET", "cart_items", params={"cart_id": f"eq.{cart['cart_id']}", "select": "cart_item_id,product_id,qty"})
        result = []
        for item in items:
            products = await _request(client, "GET", "products", params={"product_id": f"eq.{item['product_id']}", "select": "*"})
            if products:
                result.append({**item, "product": products[0]})
        return {"cart_id": cart["cart_id"], "items": result}


async def add_cart_item(payload: CartItemInput, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    profile = await get_customer_profile(credentials)
    async with httpx.AsyncClient(timeout=10) as client:
        cart = await _cart(client, profile["customer_id"])
        products = await _request(client, "GET", "products", params={"product_id": f"eq.{payload.product_id}", "select": "stok"})
        if not products:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
        existing = await _request(client, "GET", "cart_items", params={"cart_id": f"eq.{cart['cart_id']}", "product_id": f"eq.{payload.product_id}", "select": "*"})
        qty = payload.qty + (int(existing[0]["qty"]) if existing else 0)
        if qty > int(products[0]["stok"]):
            raise HTTPException(status_code=409, detail="Quantity melebihi stok.")
        if existing:
            rows = await _request(client, "PATCH", "cart_items", params={"cart_item_id": f"eq.{existing[0]['cart_item_id']}"}, body={"qty": qty}, prefer="return=representation")
        else:
            rows = await _request(client, "POST", "cart_items", body={"cart_item_id": str(uuid4()), "cart_id": cart["cart_id"], "product_id": payload.product_id, "qty": qty}, prefer="return=representation")
        return rows[0]


async def update_cart_item(cart_item_id: str, payload: CartItemInput, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    profile = await get_customer_profile(credentials)
    async with httpx.AsyncClient(timeout=10) as client:
        cart = await _cart(client, profile["customer_id"])
        products = await _request(client, "GET", "products", params={"product_id": f"eq.{payload.product_id}", "select": "stok"})
        if not products or int(payload.qty) > int(products[0]["stok"]):
            raise HTTPException(status_code=409, detail="Quantity melebihi stok.")
        rows = await _request(client, "PATCH", "cart_items", params={"cart_item_id": f"eq.{cart_item_id}", "cart_id": f"eq.{cart['cart_id']}"}, body={"qty": payload.qty}, prefer="return=representation")
        if not rows:
            raise HTTPException(status_code=404, detail="Item cart tidak ditemukan.")
        return rows[0]


async def delete_cart_item(cart_item_id: str, credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    profile = await get_customer_profile(credentials)
    async with httpx.AsyncClient(timeout=10) as client:
        cart = await _cart(client, profile["customer_id"])
        await _request(client, "DELETE", "cart_items", params={"cart_item_id": f"eq.{cart_item_id}", "cart_id": f"eq.{cart['cart_id']}"}, prefer="return=minimal")
        return {"deleted": True}


async def clear_cart(credentials: HTTPAuthorizationCredentials | None = Depends(customer_bearer)):
    profile = await get_customer_profile(credentials)
    async with httpx.AsyncClient(timeout=10) as client:
        cart = await _cart(client, profile["customer_id"])
        await _request(client, "DELETE", "cart_items", params={"cart_id": f"eq.{cart['cart_id']}"}, prefer="return=minimal")
        return {"cleared": True}
