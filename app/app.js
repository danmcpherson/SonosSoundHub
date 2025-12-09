/**
 * Fetch user authentication information from Static Web Apps
 * @returns {Promise<Object>} User information object
 */
async function getUserInfo() {
    try {
        const response = await fetch('/.auth/me');
        const payload = await response.json();
        const { clientPrincipal } = payload;
        return clientPrincipal;
    } catch (error) {
        console.error('Error fetching user info:', error);
        return null;
    }
}

/**
 * Display user information on the page
 * @param {Object} user - User information object
 */
function displayUserInfo(user) {
    const userInfoElement = document.getElementById('userInfo');
    const welcomeTitleElement = document.getElementById('welcomeTitle');
    const welcomeMessageElement = document.getElementById('welcomeMessage');
    const userProfileElement = document.getElementById('userProfile');

    if (!user) {
        // User not authenticated - redirect to login
        window.location.href = '/.auth/login/aad';
        return;
    }

    // Extract first name or use full name
    const userName = user.userDetails || 'User';
    const firstName = userName.split(' ')[0] || userName.split('@')[0];

    // Update navigation user info
    userInfoElement.textContent = userName;

    // Update welcome title and message
    welcomeTitleElement.textContent = `Welcome ${firstName}!`;
    welcomeMessageElement.textContent = `You're logged in as ${userName}`;

    // Build user profile display
    const profileHTML = `
        <div class="grid md:grid-cols-2 gap-6">
            <div class="space-y-4">
                <div class="border-b pb-4">
                    <label class="block text-sm font-semibold text-gray-600 mb-1">Username</label>
                    <p class="text-lg text-dark">${escapeHtml(user.userDetails || 'N/A')}</p>
                </div>
                <div class="border-b pb-4">
                    <label class="block text-sm font-semibold text-gray-600 mb-1">User ID</label>
                    <p class="text-lg text-dark font-mono text-sm">${escapeHtml(user.userId || 'N/A')}</p>
                </div>
                <div class="border-b pb-4">
                    <label class="block text-sm font-semibold text-gray-600 mb-1">Identity Provider</label>
                    <p class="text-lg text-dark">${escapeHtml(user.identityProvider || 'N/A')}</p>
                </div>
            </div>
            <div class="space-y-4">
                <div class="border-b pb-4">
                    <label class="block text-sm font-semibold text-gray-600 mb-1">User Roles</label>
                    <div class="flex flex-wrap gap-2 mt-2">
                        ${user.userRoles && user.userRoles.length > 0 
                            ? user.userRoles.map(role => 
                                `<span class="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm font-semibold">${escapeHtml(role)}</span>`
                            ).join('')
                            : '<span class="text-gray-500">No roles assigned</span>'
                        }
                    </div>
                </div>
                <div class="border-b pb-4">
                    <label class="block text-sm font-semibold text-gray-600 mb-1">Claims</label>
                    <div class="mt-2">
                        ${user.claims && user.claims.length > 0
                            ? `<div class="bg-gray-50 p-3 rounded max-h-40 overflow-y-auto">
                                ${user.claims.map(claim => 
                                    `<div class="text-sm mb-2">
                                        <span class="font-semibold text-gray-700">${escapeHtml(claim.typ)}:</span>
                                        <span class="text-gray-600 ml-2">${escapeHtml(claim.val)}</span>
                                    </div>`
                                ).join('')}
                               </div>`
                            : '<span class="text-gray-500">No claims available</span>'
                        }
                    </div>
                </div>
            </div>
        </div>
        <div class="mt-6 p-4 bg-blue-50 rounded-lg">
            <h4 class="font-semibold text-primary mb-2">Full User Object (Debug)</h4>
            <pre class="text-xs bg-white p-3 rounded overflow-x-auto">${JSON.stringify(user, null, 2)}</pre>
        </div>
    `;

    userProfileElement.innerHTML = profileHTML;
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

/**
 * Initialize the application
 */
async function init() {
    const user = await getUserInfo();
    displayUserInfo(user);
}

// Run initialization when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
