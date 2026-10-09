import { useParams } from "react-router";

export default function ProductPage() {
    const { productId } = useParams(); // selalu string

    return <h1>User ID: {productId}</h1>;
}