import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import Navbar from '../components/Navbar.jsx'

const getDefaultApiBaseUrl = () => {
    if (typeof window === 'undefined') {
        return 'http://localhost:8080'
    }
    const origin = window.location.origin
    const isLocalhost = origin.includes('localhost') || origin.includes('127.0.0.1')
    return isLocalhost ? 'http://localhost:8080' : `${origin}/api`
}

// const API_BASE_URL = import.meta.env.APP_API_BASE_URL || getDefaultApiBaseUrl()
const BASE_URL = import.meta.env.VITE_BASE_URL || getDefaultApiBaseUrl()

const fallbackPlatforms = [
    { label: 'TechCrunch', value: 'techcrunch' },
    { label: 'Fintech News', value: 'fintechnews' },
    { label: 'Glossy', value: 'glossy' },
    { label: 'Robb Report', value: 'robbreport' },
]

const categoryOptions = [
    { label: 'Kinh tế', value: 'Kinh tế' },
    { label: 'Bất động sản', value: 'Bất động sản' },
    { label: 'Chứng khoán', value: 'Chứng khoán' },
    { label: 'Coin', value: 'Coin' },
    { label: 'Startup', value: 'Startup' },
    { label: 'Công nghệ', value: 'Công nghệ' },
    { label: 'Beauty', value: 'Beauty' },
    { label: 'Lifestyle', value: 'Lifestyle' },
]

const HomePage = () => {
    const [links, setLinks] = useState([{ id: 1, value: '' }])
    const [platformOptions, setPlatformOptions] = useState(fallbackPlatforms)
    const [platform, setPlatform] = useState(fallbackPlatforms[0].value)
    const [category, setCategory] = useState(categoryOptions[0].value)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [isLoadingPlatforms, setIsLoadingPlatforms] = useState(true)
    const [result, setResult] = useState(null)
    const [activeArticleIndex, setActiveArticleIndex] = useState(0)
    const [isEditingArticle, setIsEditingArticle] = useState(false)
    const [isSavingEdit, setIsSavingEdit] = useState(false)
    const [isUploading, setIsUploading] = useState(false)
    const [editForm, setEditForm] = useState({
        title: '',
        category: '',
        contentsText: '',
        topicsText: '',
    })

    useEffect(() => {
        let ignore = false
        const fetchPlatforms = async () => {
            try {
                const response = await fetch(`${BASE_URL}/platforms`)
                if (!response.ok) {
                    throw new Error('Không thể tải danh sách nền tảng.')
                }
                const data = await response.json()
                if (ignore || !Array.isArray(data) || data.length === 0) return
                const supported = data.filter((item) => item.supported)
                if (supported.length === 0) return
                const normalized = supported.map((item) => ({
                    label: item.label,
                    value: item.value,
                    description: item.description,
                }))
                setPlatformOptions(normalized)
                setPlatform((prev) => {
                    const stillValid = normalized.some((option) => option.value === prev)
                    return stillValid ? prev : normalized[0].value
                })
            } catch (error) {
                console.error(error)
                toast.error('Không thể tải danh sách platform, dùng cấu hình mặc định.')
            } finally {
                if (!ignore) setIsLoadingPlatforms(false)
            }
        }

        fetchPlatforms()
        return () => {
            ignore = true
        }
    }, [])

    useEffect(() => {
        setActiveArticleIndex(0)
    }, [result])

    useEffect(() => {
        if (!result) return
        const articles = Array.isArray(result.articles) ? result.articles : []
        if (!articles.length) return
        const safeIndex = Math.min(activeArticleIndex, Math.max(articles.length - 1, 0))
        const article = articles[safeIndex]
        if (!article) return
        const contents = Array.isArray(article.contents) ? article.contents : []
        const topics = Array.isArray(article.topics) ? article.topics : article.tags || []
        setEditForm({
            title: article.article_title || article.title || '',
            category: article.category || result.category || '',
            contentsText: contents.join('\n\n'),
            topicsText: topics.join(', '),
        })
        setIsEditingArticle(false)
        setIsSavingEdit(false)
    }, [result, activeArticleIndex])

    const handleLinkChange = (index, value) => {
        setLinks((prev) =>
            prev.map((link, i) => (i === index ? { ...link, value } : link)),
        )
    }

    const addLinkField = () => {
        setLinks((prev) => [...prev, { id: Date.now(), value: '' }])
    }

    const handleSubmit = async (event) => {
        event.preventDefault()
        const sanitizedLinks = links.map((link) => link.value.trim()).filter(Boolean)

        if (!sanitizedLinks.length) {
            toast.error('Vui lòng nhập ít nhất một link hợp lệ.')
            return
        }

        if (!platform) {
            toast.error('Vui lòng chọn nền tảng.')
            return
        }

        setIsSubmitting(true)
        setResult(null)
        try {
            const payload = {
                links: sanitizedLinks,
                platform,
                category,
                convert_markdown: true,
            }
            const response = await fetch(`${BASE_URL}/crawl`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })
            if (!response.ok) {
                const errorMessage = await response
                    .json()
                    .catch(() => ({ detail: 'Có lỗi xảy ra' }))
                throw new Error(errorMessage.detail || 'Không thể xử lý yêu cầu.')
            }
            const data = await response.json()
            setResult(data)
            toast.success('Crawl thành công!')
        } catch (error) {
            console.error(error)
            toast.error(error.message || 'Có lỗi xảy ra.')
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleUpload = async () => {
        if (!result?.output_path) {
            toast.error('Vui lòng crawl dữ liệu trước khi đăng bài.')
            return
        }

        setIsUploading(true)
        try {
            const response = await fetch(`${BASE_URL}/upload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_path: result.output_path }),
            })
            if (!response.ok) {
                const errorMessage = await response
                    .json()
                    .catch(() => ({ detail: 'Không thể đăng bài.' }))
                throw new Error(errorMessage.detail || 'Không thể đăng bài.')
            }
            const data = await response.json()
            toast.success(
                `Đã gửi yêu cầu đăng ${data.success}/${data.total} bài (thất bại: ${data.failed}).`,
            )
        } catch (error) {
            console.error(error)
            toast.error(error.message || 'Không thể đăng bài.')
        } finally {
            setIsUploading(false)
        }
    }

    const handleEditFieldChange = (field, value) => {
        setEditForm((prev) => ({ ...prev, [field]: value }))
    }

    const handleSaveEdit = async (articleIndex, originalArticle) => {
        if (!result) return
        const contentsArray = editForm.contentsText
            .split(/\n{2,}/)
            .map((item) => item.trim())
            .filter(Boolean)
        const topicsArray = editForm.topicsText
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean)

        const updatedArticle = {
            ...originalArticle,
            article_title: editForm.title,
            title: editForm.title,
            category: editForm.category,
            contents: contentsArray,
            topics: topicsArray,
        }

        setIsSavingEdit(true)
        try {
            const response = await fetch(`${BASE_URL}/articles/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    output_path: result.output_path,
                    index: articleIndex,
                    article: updatedArticle,
                }),
            })
            if (!response.ok) {
                const errorMessage = await response
                    .json()
                    .catch(() => ({ detail: 'Không thể lưu chỉnh sửa.' }))
                throw new Error(errorMessage.detail || 'Không thể lưu chỉnh sửa.')
            }
            const data = await response.json()
            setResult((prev) =>
                prev
                    ? {
                        ...prev,
                        articles: data.articles,
                    }
                    : prev,
            )
            toast.success('Đã lưu chỉnh sửa!')
            setIsEditingArticle(false)
        } catch (error) {
            console.error(error)
            toast.error(error.message || 'Không thể lưu chỉnh sửa.')
        } finally {
            setIsSavingEdit(false)
        }
    }

    const renderResult = () => {
        if (!result) return null
        const articles = Array.isArray(result.articles) ? result.articles : []
        const safeIndex = Math.min(activeArticleIndex, Math.max(articles.length - 1, 0))
        const activeArticle = articles[safeIndex] || null

        return (
            <div className="mt-10 rounded-3xl border border-red-100 bg-red-50 p-6 text-red-900">
                <div className="flex flex-col gap-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.3em] text-red-500">
                        Kết quả
                    </p>
                    <h3 className="text-2xl font-semibold text-red-700">
                        {articles.length} bài viết đã được xử lý
                    </h3>
                </div>
                {articles.length > 0 && activeArticle && (
                    <div className="mt-6 space-y-4">
                        <div className="flex flex-wrap gap-2">
                            {articles.map((article, index) => {
                                const title = article.article_title || article.title || `Bài ${index + 1}`
                                const isActive = index === safeIndex
                                return (
                                    <button
                                        type="button"
                                        key={`${title}-${index}`}
                                        onClick={() => setActiveArticleIndex(index)}
                                        className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] transition ${isActive
                                            ? 'bg-red-600 text-white shadow-lg'
                                            : 'bg-red-100 text-red-600 hover:bg-red-200'
                                            }`}
                                    >
                                        {index + 1}. {title.length > 30 ? `${title.slice(0, 30)}…` : title}
                                    </button>
                                )
                            })}
                        </div>

                        <article className="rounded-3xl bg-white p-6 shadow-md">
                            {(() => {
                                const title = activeArticle.article_title || activeArticle.title || 'Không tiêu đề'
                                const categoryLabel = activeArticle.category || result.category || 'N/A'
                                const contents = Array.isArray(activeArticle.contents)
                                    ? activeArticle.contents
                                    : []
                                const topics = Array.isArray(activeArticle.topics)
                                    ? activeArticle.topics
                                    : activeArticle.tags || []
                                return (
                                    <>
                                        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                                            <div className="space-y-2">
                                                <p className="text-sm font-semibold uppercase tracking-[0.3em] text-red-400">
                                                    Bài viết {safeIndex + 1}/{articles.length}
                                                </p>
                                                <h4 className="text-2xl font-semibold text-red-700">{title}</h4>
                                                <div className="text-xs text-red-500">
                                                    <span>Category: {categoryLabel}</span>
                                                    {'slug' in activeArticle && (
                                                        <span className="ml-3 text-red-400">Slug: {activeArticle.slug}</span>
                                                    )}
                                                </div>
                                                {topics.length > 0 && !isEditingArticle && (
                                                    <div className="flex flex-wrap gap-2 text-[11px] text-red-500">
                                                        {topics.map((topic, idx) => (
                                                            <span
                                                                key={`${topic}-${idx}`}
                                                                className="rounded-full bg-red-50 px-3 py-1 font-medium"
                                                            >
                                                                {topic}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                            <div className="flex gap-2 text-xs font-semibold uppercase tracking-[0.3em]">
                                                {isEditingArticle ? (
                                                    <>
                                                        <button
                                                            type="button"
                                                            onClick={() => {
                                                                setIsEditingArticle(false)
                                                                setEditForm({
                                                                    title,
                                                                    category: categoryLabel,
                                                                    contentsText: contents.join('\n\n'),
                                                                    topicsText: topics.join(', '),
                                                                })
                                                            }}
                                                            className="rounded-full border border-red-200 px-4 py-2 text-red-500 hover:border-red-400"
                                                            disabled={isSavingEdit}
                                                        >
                                                            Hủy
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={() => handleSaveEdit(safeIndex, activeArticle)}
                                                            className="rounded-full bg-red-600 px-4 py-2 text-white hover:bg-red-500 disabled:opacity-60"
                                                            disabled={isSavingEdit}
                                                        >
                                                            {isSavingEdit ? 'Đang lưu...' : 'Lưu'}
                                                        </button>
                                                    </>
                                                ) : (
                                                    <button
                                                        type="button"
                                                        onClick={() => setIsEditingArticle(true)}
                                                        className="rounded-full border border-red-200 px-4 py-2 text-red-600 hover:border-red-400"
                                                    >
                                                        Edit
                                                    </button>
                                                )}
                                            </div>
                                        </div>

                                        {isEditingArticle ? (
                                            <div className="mt-6 space-y-4">
                                                <label className="block text-xs font-semibold uppercase tracking-[0.3em] text-red-500">
                                                    Tiêu đề
                                                    <input
                                                        type="text"
                                                        value={editForm.title}
                                                        onChange={(event) => handleEditFieldChange('title', event.target.value)}
                                                        className="mt-2 w-full rounded-2xl border border-red-100 px-4 py-3 text-sm text-red-900 outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100"
                                                    />
                                                </label>
                                                <label className="block text-xs font-semibold uppercase tracking-[0.3em] text-red-500">
                                                    Category
                                                    <input
                                                        type="text"
                                                        value={editForm.category}
                                                        onChange={(event) => handleEditFieldChange('category', event.target.value)}
                                                        className="mt-2 w-full rounded-2xl border border-red-100 px-4 py-3 text-sm text-red-900 outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100"
                                                    />
                                                </label>
                                                <label className="block text-xs font-semibold uppercase tracking-[0.3em] text-red-500">
                                                    Topics (phân tách bằng dấu phẩy)
                                                    <input
                                                        type="text"
                                                        value={editForm.topicsText}
                                                        onChange={(event) =>
                                                            handleEditFieldChange('topicsText', event.target.value)
                                                        }
                                                        className="mt-2 w-full rounded-2xl border border-red-100 px-4 py-3 text-sm text-red-900 outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100"
                                                    />
                                                </label>
                                                <label className="block text-xs font-semibold uppercase tracking-[0.3em] text-red-500">
                                                    Nội dung (mỗi đoạn cách nhau 1 dòng trống)
                                                    <textarea
                                                        value={editForm.contentsText}
                                                        onChange={(event) =>
                                                            handleEditFieldChange('contentsText', event.target.value)
                                                        }
                                                        rows={12}
                                                        className="mt-2 w-full rounded-2xl border border-red-100 px-4 py-3 text-sm text-red-900 outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100"
                                                    />
                                                </label>
                                            </div>
                                        ) : (
                                            <div className="mt-4 space-y-4 whitespace-pre-wrap text-sm leading-7 text-red-900">
                                                {contents.length > 0 ? (
                                                    contents.map((paragraph, idx) => (
                                                        <p key={`${title}-p-${idx}`}>{paragraph}</p>
                                                    ))
                                                ) : (
                                                    <p className="text-red-400">Không có nội dung để hiển thị.</p>
                                                )}
                                            </div>
                                        )}
                                    </>
                                )
                            })()}
                        </article>
                    </div>
                )}
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-white text-red-900">
            <Navbar />

            <section className="bg-gradient-to-br from-red-700 to-red-600 text-white">
                <div className="mx-auto max-w-5xl px-6 py-16 md:py-20">
                    <p className="text-xs font-semibold uppercase tracking-[0.6em] text-red-100">
                        NewsFlow AI
                    </p>
                    <h1 className="mt-4 text-4xl font-semibold leading-tight md:text-5xl">
                        Thông tin chuẩn xác và nhanh chóng
                    </h1>
                    <p className="mt-4 max-w-3xl text-lg text-red-100">
                        Nhập danh sách đường link, chọn nền tảng và danh mục. Hệ thống AI
                        sẽ tự động thu thập, dịch thuật và tối ưu bài viết theo chuẩn xuất bản.
                    </p>
                </div>
            </section>

            <section className="-mt-12 px-6 pb-16 md:-mt-16">
                <div className="mx-auto max-w-4xl rounded-3xl border border-red-100 bg-white p-8 shadow-2xl shadow-red-200/70">
                    <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
                        <div>
                            <div className="flex items-center justify-between">
                                <span className="text-xs font-semibold uppercase tracking-[0.4em] text-red-600">
                                    Đường link nguồn
                                </span>
                                <button
                                    type="button"
                                    onClick={addLinkField}
                                    className="text-sm font-semibold text-red-600 hover:text-red-500"
                                >
                                    + Thêm link
                                </button>
                            </div>

                            <div className="mt-4 space-y-3">
                                {links.map((link, index) => (
                                    <input
                                        key={link.id}
                                        type="url"
                                        inputMode="url"
                                        placeholder={`https://example.com/bai-viet-${index + 1}`}
                                        value={link.value}
                                        onChange={(event) =>
                                            handleLinkChange(index, event.target.value)
                                        }
                                        className="w-full rounded-2xl border border-red-100 bg-white px-4 py-3 text-base text-red-900 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100"
                                        required={index === 0}
                                    />
                                ))}
                            </div>
                            <p className="mt-2 text-xs text-red-500/70">
                                Nhập ít nhất một link, có thể thêm không giới hạn để xử lý hàng
                                loạt.
                            </p>
                        </div>

                        <div className="grid gap-4 md:grid-cols-2">
                            <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.3em] text-red-600">
                                Nền tảng
                                <select
                                    value={platform}
                                    onChange={(event) => setPlatform(event.target.value)}
                                    disabled={isLoadingPlatforms || platformOptions.length === 0}
                                    className="rounded-2xl border border-red-100 bg-white px-4 py-3 text-base font-medium text-red-900 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100 disabled:cursor-not-allowed disabled:bg-red-50"
                                >
                                    {platformOptions.map((option) => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                                {isLoadingPlatforms && (
                                    <span className="text-[10px] uppercase tracking-[0.4em] text-red-300">
                                        Đang tải...
                                    </span>
                                )}
                            </label>
                            <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.3em] text-red-600">
                                Category
                                <select
                                    value={category}
                                    onChange={(event) => setCategory(event.target.value)}
                                    className="rounded-2xl border border-red-100 bg-white px-4 py-3 text-base font-medium text-red-900 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100"
                                >
                                    {categoryOptions.map((option) => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                            </label>
                        </div>

                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="mt-4 inline-flex items-center justify-center rounded-full bg-red-600 px-6 py-3 text-sm font-semibold uppercase tracking-[0.4em] text-white transition hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-70"
                        >
                            {isSubmitting ? 'Đang xử lý...' : 'Gửi yêu cầu'}
                        </button>
                    </form>

                    {renderResult()}
                </div>
            </section>

            <section className="px-6 pb-24">
                <div className="mx-auto flex max-w-4xl flex-col items-center gap-3 text-center">
                    <button
                        type="button"
                        onClick={handleUpload}
                        disabled={!result || isUploading}
                        className="inline-flex items-center justify-center rounded-full bg-red-700 px-6 py-3 text-xs font-semibold uppercase tracking-[0.4em] text-white transition hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {isUploading ? 'Đang đăng...' : 'Đăng bài'}
                    </button>
                    <p className="text-xs text-red-500">
                        {result?.output_path
                            ? ''
                            : 'Cần crawl dữ liệu trước khi đăng bài.'}
                    </p>
                </div>
            </section>
        </div>
    )
}

export default HomePage
