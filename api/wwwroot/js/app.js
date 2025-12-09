/**
 * Main Application Controller
 */

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    console.log('SonosSoundHub initialized');

    // Setup tab navigation
    setupTabNavigation();

    // Setup event listeners
    setupEventListeners();

    // Initialize speakers
    await speakers.init();
});

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Discover speakers button
    document.getElementById('discover-btn').addEventListener('click', async () => {
        await speakers.discover();
    });

    // New macro button
    document.getElementById('new-macro-btn').addEventListener('click', () => {
        macros.create();
    });

    // Macro modal close button
    document.getElementById('close-modal').addEventListener('click', () => {
        toggleMacroModal(false);
    });

    // Cancel macro button
    document.getElementById('cancel-macro-btn').addEventListener('click', () => {
        toggleMacroModal(false);
    });

    // Macro form submit
    document.getElementById('macro-form').addEventListener('submit', async (e) => {
        await macros.save(e);
    });

    // Close modal when clicking outside
    document.getElementById('macro-editor-modal').addEventListener('click', (e) => {
        if (e.target.id === 'macro-editor-modal') {
            toggleMacroModal(false);
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // ESC to close modal
        if (e.key === 'Escape') {
            const modal = document.getElementById('macro-editor-modal');
            if (modal.classList.contains('active')) {
                toggleMacroModal(false);
            }
        }

        // Ctrl/Cmd + N for new macro (when on macros tab)
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            const macrosTab = document.getElementById('macros-tab');
            if (macrosTab.classList.contains('active')) {
                e.preventDefault();
                macros.create();
            }
        }

        // Ctrl/Cmd + R to refresh speakers
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            const speakersTab = document.getElementById('speakers-tab');
            if (speakersTab.classList.contains('active')) {
                e.preventDefault();
                speakers.discover();
            }
        }
    });
}

// Global error handler
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
});
