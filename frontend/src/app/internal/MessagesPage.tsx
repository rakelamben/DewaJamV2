/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import {
  getInternalMessages,
  getInternalPersonnel,
  markInternalMessageRead,
  sendInternalMessage,
  type InternalMessage,
  type InternalPersonnel,
} from "../../../lib/api"
import { useAuth } from "../../auth/AuthContext"

export default function MessagesPage() {
  const { session } = useAuth()
  const [messages, setMessages] = useState<InternalMessage[]>([])
  const [people, setPeople] = useState<InternalPersonnel[]>([])
  const [receiver, setReceiver] = useState("")
  const [subject, setSubject] = useState("")
  const [body, setBody] = useState("")
  const [loading, setLoading] = useState(false)
  const [messagesLoading, setMessagesLoading] = useState(true)
  const [peopleLoading, setPeopleLoading] = useState(true)

  const loadMessages = useCallback(async () => {
    if (!session) return
    setMessagesLoading(true)
    try {
      setMessages(await getInternalMessages(session.access_token))
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Pesan gagal dimuat.")
    } finally {
      setMessagesLoading(false)
    }
  }, [session])

  const loadPersonnel = useCallback(async () => {
    if (!session) return
    setPeopleLoading(true)
    try {
      setPeople(await getInternalPersonnel(session.access_token))
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Direktori personnel gagal dimuat.")
    } finally {
      setPeopleLoading(false)
    }
  }, [session])

  useEffect(() => {
    void loadMessages()
    void loadPersonnel()
  }, [loadMessages, loadPersonnel])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!session || !receiver || !body.trim()) return
    setLoading(true)
    try {
      await sendInternalMessage(session.access_token, {
        receiver_id: receiver,
        subject,
        body,
      })
      setReceiver("")
      setSubject("")
      setBody("")
      await loadMessages()
      toast.success("Pesan berhasil dikirim.")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Pesan gagal dikirim.")
    } finally {
      setLoading(false)
    }
  }

  async function read(message: InternalMessage) {
    if (!session || message.is_read) return
    try {
      await markInternalMessageRead(session.access_token, message.message_id)
      setMessages((current) =>
        current.map((item) =>
          item.message_id === message.message_id
            ? { ...item, is_read: true }
            : item
        )
      )
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Pesan gagal diperbarui.")
    }
  }

  return (
    <main className="grid gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Pesan Internal</h1>
        <p className="text-sm text-muted-foreground">
          Komunikasi antar-personel toko.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader>
            <CardTitle>Inbox</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            {messagesLoading ? (
              <p className="text-sm text-muted-foreground">Memuat pesan...</p>
            ) : messages.length === 0 ? (
              <p className="text-sm text-muted-foreground">Belum ada pesan.</p>
            ) : (
              messages.map((message) => (
                <button
                  type="button"
                  className={`rounded-lg border p-4 text-left ${
                    message.is_read ? "opacity-60" : "bg-muted/30"
                  }`}
                  key={message.message_id}
                  onClick={() => void read(message)}
                >
                  <p className="font-medium">
                    {message.subject || "Pesan internal"}
                  </p>
                  <p className="mt-1 line-clamp-2 text-sm">{message.body}</p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {new Date(message.created_at).toLocaleString("id-ID")}
                    {!message.is_read && " · Belum dibaca"}
                  </p>
                </button>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tulis pesan</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="grid gap-4" onSubmit={submit}>
              <div className="grid gap-2">
                <Label>Penerima</Label>
                <Select
                  value={receiver}
                  onValueChange={(value) => setReceiver(value ?? "")}
                  disabled={peopleLoading || people.length === 0}
                  required
                >
                  <SelectTrigger className="w-full">
                    <SelectValue
                      placeholder={
                        peopleLoading
                          ? "Memuat personnel..."
                          : people.length === 0
                            ? "Personnel tidak tersedia"
                            : "Pilih personnel"
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {people.map((person) => (
                      <SelectItem
                        key={person.personnel_id}
                        value={person.personnel_id}
                      >
                        {person.nama} — {person.role || person.personnel_type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label>Subjek</Label>
                <Input
                  value={subject}
                  onChange={(event) => setSubject(event.target.value)}
                />
              </div>

              <div className="grid gap-2">
                <Label>Pesan</Label>
                <textarea
                  className="min-h-28 rounded-lg border bg-background p-3 text-sm"
                  value={body}
                  onChange={(event) => setBody(event.target.value)}
                  required
                />
              </div>

              <Button type="submit" disabled={loading || peopleLoading || !receiver}>
                {loading ? "Mengirim..." : "Kirim Pesan"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  )
}
