# Future Enhancements — InsightFlow AI

Roadmap of improvements and features to add after MVP launch.

---

## High Priority (Next Sprint)

- [ ] **Real SSE Streaming** — Replace fake typewriter with actual Server-Sent Events from LLM
- [ ] **HDFC Ergo Policy Sample** — Add insurance policy document as pre-indexed sample
- [ ] **3rd Sample Document** — Add a third domain document (tech/business)
- [ ] **Conversational Memory** — Multi-turn context (remember previous questions in session)

## Medium Priority

- [ ] **Background Indexing** — Large document processing with progress polling endpoint
- [ ] **Persistent Vector Store** — Redis/PostgreSQL backed sessions surviving restarts
- [ ] **User Authentication** — Optional login for saved chat history
- [ ] **Per-session Rate Limiting** — Prevent abuse of free default model
- [ ] **More File Formats** — HTML, Markdown, EPUB, plain text URLs
- [ ] **OCR Support** — Scanned PDF text extraction
- [ ] **Chunk Highlighting** — Show which part of source document was used

## Low Priority (Future)

- [ ] **Model Auto-discovery** — Fetch available models from provider APIs dynamically
- [ ] **Analytics Dashboard** — Usage stats, popular documents, error rates
- [ ] **WebSocket Real-time** — Replace polling with WebSocket for instant updates
- [ ] **Multi-document Chat** — Upload multiple docs, ask cross-document questions
- [ ] **Export Chat** — Download conversation as PDF/Markdown
- [ ] **Custom Embeddings** — Let user choose embedding model
- [ ] **Docker Deployment** — Containerized backend for self-hosting
- [ ] **Internationalization** — Multi-language UI support

## Infrastructure

- [ ] **Redis Sessions** — Move from in-memory dict to Redis for multi-worker support
- [ ] **Worker Scaling** — Multiple Gunicorn workers behind load balancer
- [ ] **CDN for Frontend** — CloudFlare or similar for faster asset loading
- [ ] **Monitoring** — Error tracking (Sentry), uptime monitoring
- [ ] **CI/CD Pipeline** — GitHub Actions for automated testing and deployment

---

*Last updated: August 2026*
