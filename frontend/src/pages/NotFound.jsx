const NotFound = () => {
    return (
        <div className="min-h-screen bg-slate-900 text-slate-100 bg-[url('assets/notfound.png')] bg-cover bg-center h-screen">
            <section className="mx-auto flex max-w-4xl flex-col items-center gap-4 px-6 py-20 text-center">
                <a
                    href="/"
                    className="rounded-full border border-white/30 px-6 py-2 text-sm font-semibold uppercase tracking-wide text-white transition hover:bg-white/10"
                >
                    Về trang chủ
                </a>
            </section>
        </div>
    )
}

export default NotFound
