/* eslint-disable react-hooks/set-state-in-effect, react-hooks/exhaustive-deps */
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Package, Plus, RefreshCw, Search } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  getWarehouseMovements,
  getWarehouseStock,
  createWarehouseMovement,
  createStockWorkflow,
  type WarehouseMovement,
  type WarehouseStock,
} from "../../../lib/api";
import { useAuth } from "../../auth/AuthContext";

const movementTypes = [
  "purchase_in",
  "sale_out",
  "return_in",
  "return_out",
  "adjustment",
  "damaged",
] as const;
const emptyForm = {
  product_id: "",
  tipe_mutasi: "purchase_in",
  qty_change: "",
  alasan: "",
};

export default function WarehousePage() {
  const { session } = useAuth();
  const [stock, setStock] = useState<WarehouseStock[]>([]);
  const [movements, setMovements] = useState<WarehouseMovement[]>([]);
  const [search, setSearch] = useState("");
  const [stockFilter, setStockFilter] = useState("all");
  const [movementFilter, setMovementFilter] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  async function load() {
    if (!session) return;
    setLoading(true);
    try {
      const [stockRows, movementRows] = await Promise.all([
        getWarehouseStock(session.access_token),
        getWarehouseMovements(
          session.access_token,
          movementFilter ? { tipe_mutasi: movementFilter } : undefined
        ),
      ]);
      setStock(stockRows);
      setMovements(movementRows);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Data warehouse gagal dimuat."
      );
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [session, movementFilter]);
  const visibleStock = useMemo(
    () =>
      stock.filter((product) => {
        const matchesSearch = `${product.nama_barang} ${product.brand ?? ""} ${
          product.kategori ?? ""
        }`
          .toLowerCase()
          .includes(search.toLowerCase());
        const matchesStock =
          stockFilter === "all" ||
          (stockFilter === "empty" && product.stok === 0) ||
          (stockFilter === "low" && product.stok > 0 && product.stok <= 5);
        return matchesSearch && matchesStock;
      }),
    [stock, search, stockFilter]
  );
  const selectedProduct = stock.find(
    (product) => product.product_id === form.product_id
  );
  const delta = Number(form.qty_change || 0);
  const previewStock = selectedProduct
    ? selectedProduct.stok +
      (form.tipe_mutasi === "adjustment"
        ? delta
        : ["purchase_in", "return_in"].includes(form.tipe_mutasi)
        ? Math.abs(delta)
        : -Math.abs(delta))
    : null;
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!session) return;
    if (
      !form.product_id ||
      !form.alasan.trim() ||
      !form.qty_change ||
      Number(form.qty_change) === 0
    ) {
      toast.error("Lengkapi produk, quantity, dan alasan.");
      return;
    }
    setSaving(true);
    try {
      const requiresApproval = ["adjustment", "damaged", "return_in", "return_out"].includes(form.tipe_mutasi)
      const payload = {
        product_id: form.product_id,
        tipe_mutasi: form.tipe_mutasi,
        qty_change: Number(form.qty_change),
        alasan: form.alasan.trim(),
      }
      if (requiresApproval) {
        await createStockWorkflow(session.access_token, payload)
      } else {
        await createWarehouseMovement(session.access_token, payload)
      }
      setOpen(false);
      setForm(emptyForm);
      await load();
      toast.success(requiresApproval ? "Request approval berhasil dibuat." : "Mutasi stok berhasil dibuat.");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Mutasi stok gagal dibuat."
      );
    } finally {
      setSaving(false);
    }
  }
  return (
    <main className="p-6 grid gap-6">
      {open && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4">
          <Card className="w-full min-w-0 max-w-md">
            <CardHeader>
              <CardTitle>Buat Mutasi Stok</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="grid gap-4" onSubmit={submit}>
                <div className="grid gap-2">
                  <Label>Produk</Label>
                  <select
                    className="min-w-0 h-9 rounded-lg border bg-background px-3 text-sm"
                    value={form.product_id}
                    onChange={(event) =>
                      setForm({ ...form, product_id: event.target.value })
                    }
                    required
                  >
                    <option value="">Pilih produk</option>
                    {stock.map((product) => (
                      <option
                        key={product.product_id}
                        value={product.product_id}
                      >
                        {product.nama_barang} — stok {product.stok}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid gap-2">
                  <Label>Tipe mutasi</Label>
                  <select
                    className="min-w-0 h-9 rounded-lg border bg-background px-3 text-sm"
                    value={form.tipe_mutasi}
                    onChange={(event) =>
                      setForm({ ...form, tipe_mutasi: event.target.value })
                    }
                  >
                    {movementTypes.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid gap-2">
                  <Label>
                    {form.tipe_mutasi === "adjustment"
                      ? "Perubahan stok (+/-)"
                      : "Quantity"}
                  </Label>
                  <Input
                    type="number"
                    className="min-w-0"
                    min={form.tipe_mutasi === "adjustment" ? undefined : 1}
                    value={form.qty_change}
                    onChange={(event) =>
                      setForm({ ...form, qty_change: event.target.value })
                    }
                    required
                  />
                  {selectedProduct && (
                    <p className="text-xs text-muted-foreground">
                      Stok: {selectedProduct.stok} → {previewStock}
                    </p>
                  )}
                </div>
                <div className="grid gap-2">
                  <Label>Alasan</Label>
                  <textarea
                    className="min-w-0 min-h-24 rounded-lg border bg-background p-3 text-sm"
                    value={form.alasan}
                    onChange={(event) =>
                      setForm({ ...form, alasan: event.target.value })
                    }
                    placeholder="Tuliskan alasan mutasi..."
                    required
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setOpen(false)}
                  >
                    Batal
                  </Button>
                  <Button type="submit" disabled={saving}>
                    {saving ? "Menyimpan..." : "Simpan Mutasi"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>

      )}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Warehouse</h1>
          <p className="text-sm text-muted-foreground">
            Pantau stok dan catat mutasi produk.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => void load()}>
            <RefreshCw /> Refresh
          </Button>
          <Button onClick={() => setOpen(true)}>
            <Plus /> Buat Mutasi
          </Button>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-3 p-5">
            <Package className="text-primary" />
            <div>
              <p className="text-sm text-muted-foreground">Total produk</p>
              <p className="text-2xl font-semibold">{stock.length}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Stok habis</p>
            <p className="text-2xl font-semibold text-destructive">
              {stock.filter((item) => item.stok === 0).length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Stok rendah</p>
            <p className="text-2xl font-semibold text-amber-600">
              {stock.filter((item) => item.stok > 0 && item.stok <= 5).length}
            </p>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Monitoring Stok</CardTitle>
          <div className="flex flex-wrap gap-2">
            <div className="relative max-w-sm flex-1">
              <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Cari produk..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
            <select
              className="h-9 rounded-lg border bg-background px-3 text-sm"
              value={stockFilter}
              onChange={(event) => setStockFilter(event.target.value)}
            >
              <option value="all">Semua stok</option>
              <option value="empty">Stok habis</option>
              <option value="low">Stok rendah</option>
            </select>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="h-40 animate-pulse rounded bg-muted" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Produk</TableHead>
                  <TableHead>Kategori</TableHead>
                  <TableHead>Harga</TableHead>
                  <TableHead>Stok</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visibleStock.map((product) => (
                  <TableRow key={product.product_id}>
                    <TableCell className="font-medium">
                      {product.nama_barang}
                      <br />
                      <span className="text-xs text-muted-foreground">
                        {product.brand || "-"}
                      </span>
                    </TableCell>
                    <TableCell>{product.kategori || "-"}</TableCell>
                    <TableCell>
                      Rp {Number(product.harga).toLocaleString("id-ID")}
                    </TableCell>
                    <TableCell>
                      <span
                        className={
                          product.stok === 0
                            ? "text-destructive"
                            : product.stok <= 5
                            ? "text-amber-600"
                            : "text-emerald-600"
                        }
                      >
                        {product.stok}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>Riwayat Mutasi</CardTitle>
            <select
              className="h-9 rounded-lg border bg-background px-3 text-sm"
              value={movementFilter}
              onChange={(event) => setMovementFilter(event.target.value)}
            >
              <option value="">Semua tipe</option>
              {movementTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Waktu</TableHead>
                <TableHead>Produk</TableHead>
                <TableHead>Tipe</TableHead>
                <TableHead>Perubahan</TableHead>
                <TableHead>Stok</TableHead>
                <TableHead>Alasan</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {movements.map((movement) => (
                <TableRow key={movement.movement_id}>
                  <TableCell>
                    {new Date(movement.created_at).toLocaleString("id-ID")}
                  </TableCell>
                  <TableCell>
                    {movement.product?.nama_barang || movement.product_id}
                  </TableCell>
                  <TableCell>{movement.tipe_mutasi}</TableCell>
                  <TableCell
                    className={
                      movement.qty_change < 0
                        ? "text-destructive"
                        : "text-emerald-600"
                    }
                  >
                    {movement.qty_change > 0 ? "+" : ""}
                    {movement.qty_change}
                  </TableCell>
                  <TableCell>
                    {movement.stok_sebelum} → {movement.stok_sesudah}
                  </TableCell>
                  <TableCell className="max-w-xs whitespace-normal">
                    {movement.alasan || "-"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {!loading && movements.length === 0 && (
            <p className="p-8 text-center text-muted-foreground">
              Belum ada mutasi stok.
            </p>
          )}
        </CardContent>
      </Card>

    </main>
  );
}
