/**
 * InsightFlow AI â€” Frontend Configuration
 * API base URL and app settings.
 */

const CONFIG = {
    // Backend API URL (change for production)
    API_BASE_URL: 'https://insightflow-ai-backend-ki7d.onrender.com',
    // Production: 'https://insightflow-ai-backend.onrender.com'

    // App settings
    MAX_FILE_SIZE_MB: 10,
    SUPPORTED_EXTENSIONS: ['.pdf', '.txt', '.docx'],
    TYPEWRITER_DELAY_MS: 30,

    // Provider â†’ Model mapping
    PROVIDERS: {
        tokenrouter: {
            name: 'TokenRouter',
            icon: 'ðŸ”—',
            color: '#00cec9',
            models: [
                { id: 'qwen/qwen3.8-max-free', name: 'Qwen 3.8 Max (Free)' },
                { id: 'moonshotai/kimi-k3', name: 'Moonshot Kimi K3' },
            ],
            allowsCustom: true,
            requiresKey: false,
            hint: 'Free default model â€” no API key needed!'
        },
        direct: {
            name: 'Direct',
            icon: 'âš¡',
            color: '#6c5ce7',
            models: [
                { id: 'claude-haiku-4-5-20251001', name: 'Claude Haiku 4.5' },
                { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash' },
            ],
            allowsCustom: false,
            requiresKey: true,
            hint: 'Requires your own API key (Anthropic or Google)'
        },
        openrouter: {
            name: 'OpenRouter',
            icon: 'ðŸŒ',
            color: '#55efc4',
            models: [
                { id: 'z-ai/glm-5.2:free', name: 'GLM 5.2 (Free)' },
                { id: 'nvidia/nemotron-3-super-120b-a12b:free', name: 'Nemotron 120B (Free)' },
            ],
            allowsCustom: true,
            requiresKey: true,
            hint: 'Requires OpenRouter API key'
        },
    },
};
