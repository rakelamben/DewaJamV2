export default function DashboardPage() {
  return (
    <>
      <div className="grid h-[calc(100dvh-var(--header-height)-2rem)] place-items-center overflow-hidden md:h-[calc(100dvh-var(--header-height)-3rem)]">
        <div className="flex flex-col gap-2 items-center">
          <p className="text-2xl font-semibold">Selamat Datang</p> 
          <p className="">Selamat Bekerja</p>
        </div>
      </div>
    </>
  )
}
