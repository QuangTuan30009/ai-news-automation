import logo from '../assets/logo.png'

const Navbar = () => {
    return (
        <header className="bg-white text-slate-900 shadow-md shadow-slate-900/5">
            <nav className="flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-4">
                <a href="/" className="flex items-center gap-3 font-semibold tracking-wide text-slate-900">
                    <span className="flex h-12 w-12 items-center justify-center rounded-full bg-red-600 p-2">
                        <img
                            src={logo}
                            alt="NewsFlow AI logo"
                            className="h-full w-full object-contain"
                        />
                    </span>
                    <span className="text-lg font-semibold text-red-600">
                        NewsFlow AI
                    </span>
                </a>
            </nav>
        </header>
    )
}

export default Navbar
