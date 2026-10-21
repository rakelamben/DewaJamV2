/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState } from "react"
import { Link, useNavigate, useParams } from "react-router"
import { Archive, BookOpen, Check, Download, RefreshCw, RotateCcw, Search, Settings, Star, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"
import { addKnowledgeBookmark, archiveKnowledgeItem, createKnowledgeAttachment, deleteKnowledgeItem, getKnowledgeAttachmentDownloadUrl, getKnowledgeAttachments, getKnowledgeBookmarks, getKnowledgeCategories, getKnowledgeItem, getKnowledgeItems, getKnowledgeUploadPath, getKnowledgeVersions, publishKnowledgeItem, removeKnowledgeBookmark, restoreKnowledgeItem, restoreKnowledgeVersion, searchKnowledge, updateKnowledgeItem, type KnowledgeAttachment, type KnowledgeCategory, type KnowledgeItem, type KnowledgeType, type KnowledgeVersion } from "../../../lib/api"
import { getSupabaseClient } from "../../../lib/supabase"
import { useAuth } from "../../auth/AuthContext"

const TYPES: Array<{ value: KnowledgeType; label: string }> = [
  { value: "policy", label: "Policy / SOP" },
  { value: "faq", label: "FAQ" },
  { value: "article", label: "Artikel" },
  { value: "video", label: "Video" },
  { value: "case_study", label: "Studi Kasus" },
]

function itemId(item: KnowledgeItem) { return item.policy_id || item.faq_id || item.article_id || item.video_id || item.case_study_id || "" }
function title(item: KnowledgeItem) { return item.judul || item.pertanyaan || "Konten knowledge" }

export default function KnowledgePage() {
  const { session } = useAuth()
  const [items, setItems] = useState<KnowledgeItem[]>([])
  const [categories, setCategories] = useState<KnowledgeCategory[]>([])
  const [query, setQuery] = useState("")
  const [type, setType] = useState<KnowledgeType | "">("")
  const [categoryId, setCategoryId] = useState("")
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!session) return
    setLoading(true)
    try {
      const [categoryRows, result] = await Promise.all([
        getKnowledgeCategories(session.access_token),
        query.trim()
          ? searchKnowledge(session.access_token, query, { knowledge_type: type || undefined, category_id: categoryId || undefined })
          : type
            ? getKnowledgeItems(session.access_token, type, { category_id: categoryId || undefined })
            : Promise.all(TYPES.map((option) => getKnowledgeItems(session.access_token, option.value, { category_id: categoryId || undefined }))).then((groups) => groups.flat()),
      ])
      setCategories(categoryRows)
      setItems(result)
    } catch (error) { toast.error(error instanceof Error ? error.message : "Knowledge gagal dimuat.") } finally { setLoading(false) }
  }, [session, query, type, categoryId])

  useEffect(() => { void load() }, [load])

  return <main className="grid gap-6 p-6"><div className="flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-2xl font-semibold">Knowledge Management</h1><p className="text-sm text-muted-foreground">Temukan SOP, FAQ, artikel, video, dan studi kasus internal.</p></div><div className="flex gap-2"><Button variant="outline" render={<Link to="/internal/masterdata/knowledge" />}><Settings /> Kelola Knowledge</Button><Button variant="outline" onClick={() => void load()} disabled={loading}><RefreshCw className={loading ? "animate-spin" : ""} /> Refresh</Button></div></div>
    <Card><CardContent className="grid gap-3 pt-6 md:grid-cols-[1fr_180px_180px_auto]"><div className="relative"><Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" /><Input className="pl-9" placeholder="Cari knowledge..." value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void load() }} /></div><select className="h-9 rounded-lg border bg-background px-3 text-sm" value={type} onChange={(event) => setType(event.target.value as KnowledgeType | "")}><option value="">Semua tipe</option>{TYPES.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}</select><select className="h-9 rounded-lg border bg-background px-3 text-sm" value={categoryId} onChange={(event) => setCategoryId(event.target.value)}><option value="">Semua kategori</option>{categories.map((category) => <option value={category.category_id} key={category.category_id}>{category.nama_kategori}</option>)}</select><Button onClick={() => void load()}>Cari</Button></CardContent></Card>
     <Card><CardHeader><CardTitle>Daftar knowledge</CardTitle></CardHeader><CardContent>{loading ? <p>Memuat knowledge...</p> : items.length === 0 ? <div className="py-10 text-center text-sm text-muted-foreground"><BookOpen className="mx-auto mb-2 size-8" />Belum ada hasil knowledge. Gunakan pencarian atau pilih tipe konten.</div> : <div className="grid gap-3">{items.map((item) => <Link className="rounded-lg border p-4 transition hover:bg-muted/50" to={`/internal/knowledge/${item.knowledge_type}/${itemId(item)}`} key={`${item.knowledge_type}-${itemId(item)}`}><div className="flex items-start justify-between gap-3"><div><p className="font-medium">{title(item)}</p><p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{item.ringkasan || item.jawaban || item.deskripsi || item.kronologi}</p></div><span className="rounded-full bg-muted px-2 py-1 text-xs">{TYPES.find((option) => option.value === item.knowledge_type)?.label}</span></div><div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground"><span>{item.category?.nama_kategori || "Tanpa kategori"}</span><span>{item.view_count || 0} views</span><span>v{String(item.nomor_versi || "1.0").replace(/^v/, "")}</span></div></Link>)}</div>}</CardContent></Card>
  </main>
}

export function KnowledgeDetailPage() {
  const { session, profile } = useAuth()
  const params = useParams<{ knowledgeType: KnowledgeType; itemId: string }>()
  const navigate = useNavigate()
  const [item, setItem] = useState<KnowledgeItem | null>(null)
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [content, setContent] = useState("")
  const [bookmarked, setBookmarked] = useState(false)
  const [attachments, setAttachments] = useState<KnowledgeAttachment[]>([])
  const [versions, setVersions] = useState<KnowledgeVersion[]>([])
  const [uploading, setUploading] = useState(false)
  const canManage = profile?.role === "admin" || profile?.role === "manager"
  const load = useCallback(async () => { if (!session || !params.knowledgeType || !params.itemId) return; try { const [result, bookmarks, nextAttachments] = await Promise.all([getKnowledgeItem(session.access_token, params.knowledgeType, params.itemId), getKnowledgeBookmarks(session.access_token), getKnowledgeAttachments(session.access_token, params.knowledgeType, params.itemId)]); setItem(result); setContent(result.konten || result.jawaban || result.deskripsi || result.kronologi || ""); setBookmarked(bookmarks.some((entry) => entry.bookmark.source_id === params.itemId)); setAttachments(nextAttachments); if (canManage) setVersions(await getKnowledgeVersions(session.access_token, params.knowledgeType, params.itemId)) } catch (error) { toast.error(error instanceof Error ? error.message : "Detail knowledge gagal dimuat.") } }, [session, params.knowledgeType, params.itemId, canManage])
  useEffect(() => { void load() }, [load])
  async function save() { if (!session || !item || !params.knowledgeType || !params.itemId) return; setSaving(true); try { const field = params.knowledgeType === "faq" ? "jawaban" : params.knowledgeType === "video" ? "deskripsi" : params.knowledgeType === "case_study" ? "kronologi" : "konten"; await updateKnowledgeItem(session.access_token, params.knowledgeType, params.itemId, { [field]: content }); setEditing(false); await load(); toast.success("Konten berhasil diperbarui.") } catch (error) { toast.error(error instanceof Error ? error.message : "Konten gagal diperbarui.") } finally { setSaving(false) } }
  async function remove() { if (!session || !item || !params.knowledgeType || !params.itemId || !window.confirm("Hapus konten ini?")) return; try { await deleteKnowledgeItem(session.access_token, params.knowledgeType, params.itemId); toast.success("Konten dihapus."); navigate("/internal/knowledge") } catch (error) { toast.error(error instanceof Error ? error.message : "Konten gagal dihapus.") } }
  async function toggleBookmark() { if (!session || !item || !params.knowledgeType || !params.itemId) return; try { if (bookmarked) { await removeKnowledgeBookmark(session.access_token, params.knowledgeType, params.itemId); setBookmarked(false); toast.success("Bookmark dihapus.") } else { await addKnowledgeBookmark(session.access_token, params.knowledgeType, params.itemId); setBookmarked(true); toast.success("Bookmark ditambahkan.") } } catch (error) { toast.error(error instanceof Error ? error.message : "Bookmark gagal diperbarui.") } }
  async function lifecycle(action: "publish" | "archive" | "restore") { if (!session || !item || !params.knowledgeType || !params.itemId) return; try { if (action === "publish") await publishKnowledgeItem(session.access_token, params.knowledgeType, params.itemId, { catatan_perubahan: "Publikasi melalui detail knowledge." }); if (action === "archive") { const reason = window.prompt("Alasan archive:"); if (!reason?.trim()) return; await archiveKnowledgeItem(session.access_token, params.knowledgeType, params.itemId, reason.trim()) } if (action === "restore") await restoreKnowledgeItem(session.access_token, params.knowledgeType, params.itemId); await load(); toast.success("Status knowledge diperbarui.") } catch (error) { toast.error(error instanceof Error ? error.message : "Status knowledge gagal diperbarui.") } }
  async function restoreSelectedVersion(version: KnowledgeVersion) { if (!session || !item || !params.knowledgeType || !params.itemId || !window.confirm(`Pulihkan versi ${version.nomor_versi} sebagai draft?`)) return; try { await restoreKnowledgeVersion(session.access_token, params.knowledgeType, params.itemId, version.version_id); await load(); toast.success("Versi dipulihkan sebagai draft.") } catch (error) { toast.error(error instanceof Error ? error.message : "Versi gagal dipulihkan.") } }
  async function uploadAttachment(file: File) { if (!session || !params.knowledgeType || !params.itemId) return; setUploading(true); let path = ""; let bucket = ""; try { const upload = await getKnowledgeUploadPath(session.access_token, params.knowledgeType, params.itemId, file); path = upload.path; bucket = upload.bucket; const result = await getSupabaseClient().storage.from(bucket).upload(path, file, { contentType: file.type, upsert: false }); if (result.error) throw result.error; await createKnowledgeAttachment(session.access_token, params.knowledgeType, params.itemId, { storage_bucket: bucket, storage_path: path, file_name: upload.file_name, mime_type: file.type || upload.mime_type, file_size: file.size }); await load(); toast.success("Lampiran berhasil diunggah.") } catch (error) { if (path && bucket) await getSupabaseClient().storage.from(bucket).remove([path]); toast.error(error instanceof Error ? error.message : "Lampiran gagal diunggah.") } finally { setUploading(false) } }
  async function downloadAttachment(attachment: KnowledgeAttachment) { if (!session) return; try { const result = await getKnowledgeAttachmentDownloadUrl(session.access_token, attachment.attachment_id); window.open(result.url, "_blank", "noopener,noreferrer") } catch (error) { toast.error(error instanceof Error ? error.message : "Lampiran gagal dibuka.") } }
  if (!item) return <main className="p-6"><p>Memuat detail knowledge...</p></main>
  return <main className="grid gap-6 p-6"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm text-muted-foreground">{item.category?.nama_kategori || "Knowledge"}</p><h1 className="text-2xl font-semibold">{title(item)}</h1><p className="mt-1 text-sm text-muted-foreground">{item.status || (item.is_published ? "published" : "draft")} · {item.view_count || 0} views · versi {item.nomor_versi || "v1.0"}</p></div><div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => void toggleBookmark()}><Star /> {bookmarked ? "Hapus Bookmark" : "Bookmark"}</Button>{canManage && <><Button variant="outline" onClick={() => setEditing((value) => !value)}>{editing ? "Batal" : "Edit"}</Button>{item.status === "draft" && <Button onClick={() => void lifecycle("publish")}><Check /> Publish</Button>}{item.status === "published" && <Button variant="outline" onClick={() => void lifecycle("archive")}><Archive /> Archive</Button>}{item.status === "archived" && <Button variant="outline" onClick={() => void lifecycle("restore")}><RotateCcw /> Restore</Button>}<Button variant="destructive" onClick={() => void remove()}>Hapus</Button></>}</div></div><Card><CardContent className="prose max-w-none pt-6"><p className="whitespace-pre-wrap text-sm">{item.ringkasan || item.jawaban || item.deskripsi || item.kronologi}</p>{editing ? <div className="mt-6 grid gap-3"><Label>Isi konten</Label><textarea className="min-h-64 rounded-lg border bg-background px-3 py-2 text-sm" value={content} onChange={(event) => setContent(event.target.value)} /><Button onClick={() => void save()} disabled={saving}>{saving ? "Menyimpan..." : "Simpan Perubahan"}</Button></div> : <div className="mt-6 whitespace-pre-wrap text-sm">{item.konten || item.jawaban || item.deskripsi || item.video_url || item.kronologi || "Belum ada isi."}</div>}</CardContent></Card><div className="grid gap-6 lg:grid-cols-2"><Card><CardHeader><CardTitle>Lampiran</CardTitle></CardHeader><CardContent className="grid gap-3">{canManage && <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed p-3 text-sm"><Upload /> {uploading ? "Mengunggah..." : "Tambah lampiran"}<input className="hidden" type="file" disabled={uploading} onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadAttachment(file); event.currentTarget.value = "" }} /></label>}{attachments.length === 0 ? <p className="text-sm text-muted-foreground">Belum ada lampiran.</p> : attachments.map((attachment) => <div className="flex items-center justify-between gap-3 rounded border p-3" key={attachment.attachment_id}><span className="truncate text-sm">{attachment.file_name || attachment.nama_file}</span><Button variant="outline" size="sm" onClick={() => void downloadAttachment(attachment)}><Download /> Buka</Button></div>)}</CardContent></Card>{canManage && <Card><CardHeader><CardTitle>Riwayat versi</CardTitle></CardHeader><CardContent className="grid gap-3">{versions.length === 0 ? <p className="text-sm text-muted-foreground">Belum ada riwayat versi.</p> : versions.map((version) => <div className="flex items-center justify-between gap-3 rounded border p-3" key={version.version_id}><div><p className="text-sm font-medium">{version.nomor_versi} · {version.change_type || "update"}</p><p className="text-xs text-muted-foreground">{version.catatan_perubahan || "Tanpa catatan"}</p></div><Button variant="ghost" size="sm" onClick={() => void restoreSelectedVersion(version)}><RotateCcw /> Restore</Button></div>)}</CardContent></Card>}</div></main>
}
