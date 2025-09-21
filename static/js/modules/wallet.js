// DECTERUM Wallet Module

let walletData = {
    balance: 0,
    transactions: [],
    miningStats: {},
    blockchainMode: 'simple'  // 'simple' ou 'real'
};

let sessionStartTime = Date.now();
let exchangeRates = {};

// Load wallet data
async function loadWalletData() {
    try {
        const response = await fetch('/api/wallet/info');
        if (response.ok) {
            const data = await response.json();
            walletData.balance = data.balance;
            walletData.transactions = data.recent_transactions;
            updateWalletUI();
        }
    } catch (error) {
        console.error('Error loading wallet:', error);
    }
}

// Update wallet UI
function updateWalletUI() {
    // Update balance displays
    document.getElementById('wallet-balance').textContent = walletData.balance.toFixed(4);
    document.getElementById('modal-wallet-balance').textContent = walletData.balance.toFixed(4);
    document.getElementById('stars-modal-balance').textContent = walletData.balance.toFixed(4);

    // Calculate earnings by type
    const earnings = calculateEarnings();
    document.getElementById('total-earned').textContent = `${earnings.total.toFixed(4)} DTC`;
    document.getElementById('mining-earned').textContent = `${earnings.mining.toFixed(4)} DTC`;
    document.getElementById('content-earned').textContent = `${earnings.content.toFixed(4)} DTC`;

    // Update transaction history
    renderTransactions();
}

// Calculate earnings by type
function calculateEarnings() {
    let total = 0;
    let mining = 0;
    let content = 0;

    walletData.transactions.forEach(tx => {
        if (tx.recipient === currentUser?.user_id) {
            total += tx.amount;

            switch (tx.transaction_type) {
                case 'mining_reward':
                case 'initial_grant':
                    mining += tx.amount;
                    break;
                case 'badge_vote':
                case 'star_donation':
                    content += tx.amount;
                    break;
            }
        }
    });

    return { total, mining, content };
}

// Render transaction history
function renderTransactions() {
    const container = document.getElementById('transactions-list');

    if (walletData.transactions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">💳</div>
                <h3>No transactions yet</h3>
                <p>Your transaction history will appear here</p>
            </div>
        `;
        return;
    }

    const transactionsHTML = walletData.transactions.map(tx => {
        const isReceived = tx.recipient === currentUser?.user_id;
        const typeIcon = getTransactionIcon(tx.transaction_type);
        const typeLabel = getTransactionLabel(tx.transaction_type);

        return `
            <div class="transaction-item ${isReceived ? 'received' : 'sent'}">
                <div class="transaction-icon">${typeIcon}</div>
                <div class="transaction-info">
                    <div class="transaction-type">${typeLabel}</div>
                    <div class="transaction-details">
                        ${isReceived ? 'From:' : 'To:'} ${isReceived ? tx.sender : tx.recipient}
                    </div>
                    <div class="transaction-time">
                        ${new Date(tx.timestamp * 1000).toLocaleString()}
                    </div>
                </div>
                <div class="transaction-amount ${isReceived ? 'positive' : 'negative'}">
                    ${isReceived ? '+' : '-'}${tx.amount.toFixed(4)} DTC
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = transactionsHTML;
}

// Get transaction icon
function getTransactionIcon(type) {
    const icons = {
        'transfer': '💸',
        'badge_vote': '🏆',
        'star_donation': '⭐',
        'mining_reward': '⛏️',
        'initial_grant': '🎁'
    };
    return icons[type] || '💰';
}

// Get transaction label
function getTransactionLabel(type) {
    const labels = {
        'transfer': 'Transfer',
        'badge_vote': 'Badge Vote',
        'star_donation': 'Star Donation',
        'mining_reward': 'Mining Reward',
        'initial_grant': 'Welcome Bonus'
    };
    return labels[type] || 'Transaction';
}

// Show/Hide DTC Send Modal
function showSendDTCModal() {
    document.getElementById('modal-wallet-balance').textContent = walletData.balance.toFixed(4);
    document.getElementById('send-dtc-modal').style.display = 'block';
}

function hideSendDTCModal() {
    document.getElementById('send-dtc-modal').style.display = 'none';
    document.getElementById('dtc-recipient').value = '';
    document.getElementById('dtc-amount').value = '';
}

// Send DTC
async function sendDTC(event) {
    event.preventDefault();

    const recipient = document.getElementById('dtc-recipient').value.trim();
    const amount = parseFloat(document.getElementById('dtc-amount').value);

    if (!recipient || !amount || amount <= 0) {
        showToast('Please fill all fields correctly', 'error');
        return;
    }

    if (amount > walletData.balance) {
        showToast('Insufficient balance', 'error');
        return;
    }

    try {
        const response = await fetch('/api/wallet/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                recipient: recipient,
                amount: amount
            })
        });

        if (response.ok) {
            const result = await response.json();
            hideSendDTCModal();
            showToast(`Sent ${amount} DTC successfully!`, 'success');
            await loadWalletData();
        } else {
            const error = await response.json();
            showToast('Error: ' + error.detail, 'error');
        }
    } catch (error) {
        console.error('Error sending DTC:', error);
        showToast('Network error', 'error');
    }
}

// Show/Hide Stars Modal
function showSendStarsModal(videoId, authorId, authorName) {
    document.getElementById('star-recipient').textContent = authorName;
    document.getElementById('stars-modal-balance').textContent = walletData.balance.toFixed(4);

    // Store video info for sending
    window.currentStarTarget = { videoId, authorId, authorName };

    document.getElementById('send-stars-modal').style.display = 'block';
}

function hideSendStarsModal() {
    document.getElementById('send-stars-modal').style.display = 'none';
    document.getElementById('star-slider').value = 1;
    updateStarCount(1);
    window.currentStarTarget = null;
}

// Update star count display
function updateStarCount(stars) {
    const dtcValue = stars * 0.01;
    document.getElementById('star-count').textContent = stars;
    document.getElementById('stars-dtc-value').textContent = dtcValue.toFixed(2);
}

// Send stars
async function sendStars(event) {
    event.preventDefault();

    if (!window.currentStarTarget) {
        showToast('No video selected', 'error');
        return;
    }

    const stars = parseInt(document.getElementById('star-slider').value);
    const totalCost = stars * 0.01;

    if (totalCost > walletData.balance) {
        showToast('Insufficient balance', 'error');
        return;
    }

    try {
        const response = await fetch('/api/wallet/star-donation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                video_id: window.currentStarTarget.videoId,
                video_author: window.currentStarTarget.authorId,
                stars: stars
            })
        });

        if (response.ok) {
            const result = await response.json();
            hideSendStarsModal();
            showToast(`Sent ${stars} stars to ${window.currentStarTarget.authorName}! ⭐`, 'success');
            await loadWalletData();
        } else {
            const error = await response.json();
            showToast('Error: ' + error.detail, 'error');
        }
    } catch (error) {
        console.error('Error sending stars:', error);
        showToast('Network error', 'error');
    }
}

// Claim mining reward
async function claimMiningReward() {
    const uptimeHours = (Date.now() - sessionStartTime) / (1000 * 60 * 60);

    if (uptimeHours < 0.1) {
        showToast('Minimum uptime is 6 minutes', 'error');
        return;
    }

    try {
        const response = await fetch('/api/wallet/claim-mining-reward', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                uptime_hours: uptimeHours
            })
        });

        if (response.ok) {
            const result = await response.json();
            showToast(`Mining reward claimed: ${result.reward.toFixed(4)} DTC! ⛏️`, 'success');
            sessionStartTime = Date.now(); // Reset session timer
            await loadWalletData();
        } else {
            const error = await response.json();
            showToast('Error: ' + error.detail, 'error');
        }
    } catch (error) {
        console.error('Error claiming reward:', error);
        showToast('Network error', 'error');
    }
}

// Badge vote function (called from feed)
async function voteBadge(postId, badgeType, postAuthor) {
    if (walletData.balance < 0.01) {
        showToast('Insufficient balance for badge vote (0.01 DTC required)', 'error');
        return false;
    }

    try {
        const response = await fetch('/api/wallet/badge-vote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                post_id: postId,
                badge_type: badgeType,
                post_author: postAuthor
            })
        });

        if (response.ok) {
            const result = await response.json();
            showToast(`Badge vote successful! Creator earned 0.01 DTC 🏆`, 'success');
            await loadWalletData();
            return true;
        } else {
            const error = await response.json();
            showToast('Error: ' + error.detail, 'error');
            return false;
        }
    } catch (error) {
        console.error('Error voting badge:', error);
        showToast('Network error', 'error');
        return false;
    }
}

// Initialize wallet when wallet section is opened
function initializeWallet() {
    loadWalletData();

    // Update wallet every 30 seconds
    setInterval(loadWalletData, 30000);
}

// Blockchain mode functions
function switchBlockchainMode(mode) {
    walletData.blockchainMode = mode;

    // Update UI
    document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`${mode}-mode-btn`).classList.add('active');

    const descriptions = {
        'simple': 'Simple virtual currency for testing',
        'real': 'Real blockchain with mining & P2P network'
    };

    document.getElementById('mode-description').textContent = descriptions[mode];

    // Show/hide conversion button
    const conversionBtn = document.getElementById('conversion-btn');
    if (mode === 'real') {
        conversionBtn.style.display = 'block';
        loadExchangeRates();
    } else {
        conversionBtn.style.display = 'none';
    }

    // Reload wallet data
    loadWalletData();

    showToast(`Switched to ${mode} blockchain mode`, 'success');
}

// Exchange rate functions
async function loadExchangeRates() {
    try {
        const response = await fetch('/api/wallet/exchange-rates');
        if (response.ok) {
            exchangeRates = await response.json();
        }
    } catch (error) {
        console.error('Error loading exchange rates:', error);
    }
}

// Conversion modal functions
function showConversionModal() {
    document.getElementById('conversion-balance').textContent = walletData.balance.toFixed(4);
    updateConversionPreview();
    document.getElementById('conversion-modal').style.display = 'block';
}

function hideConversionModal() {
    document.getElementById('conversion-modal').style.display = 'none';
}

function updateConversionPreview() {
    const amount = parseFloat(document.getElementById('conversion-amount').value) || 100;
    const toCurrency = document.getElementById('conversion-currency').value;

    // Simulated conversion calculation
    const rates = {
        'USDT': 0.01,
        'USDC': 0.01,
        'BTC': 0.0000002,
        'ETH': 0.000003,
        'BNB': 0.000025,
        'ADA': 0.01
    };

    const rate = rates[toCurrency] || 0.01;
    const grossAmount = amount * rate;
    const exchangeFee = grossAmount * 0.01; // 1%
    const networkFees = {
        'USDT': 1.0,
        'USDC': 1.0,
        'BTC': 0.0001,
        'ETH': 0.002,
        'BNB': 0.001,
        'ADA': 0.17
    };
    const networkFee = networkFees[toCurrency] || 0.001;
    const finalAmount = grossAmount - exchangeFee - networkFee;

    // Update preview
    document.getElementById('convert-from-amount').textContent = amount.toFixed(0);
    document.getElementById('convert-to-amount').textContent = finalAmount.toFixed(6);
    document.getElementById('convert-to-currency').textContent = toCurrency;

    // Update details
    document.getElementById('exchange-rate').textContent = `1 DTC = ${rate.toFixed(8)} ${toCurrency}`;
    document.getElementById('network-fee').textContent = `~${networkFee} ${toCurrency}`;
    document.getElementById('exchange-fee').textContent = `${exchangeFee.toFixed(6)} ${toCurrency}`;
    document.getElementById('final-amount').textContent = `~${finalAmount.toFixed(6)} ${toCurrency}`;
}

// Convert crypto function
async function convertCrypto(event) {
    event.preventDefault();

    const amount = parseFloat(document.getElementById('conversion-amount').value);
    const toCurrency = document.getElementById('conversion-currency').value;

    if (!amount || amount <= 0) {
        showToast('Please enter a valid amount', 'error');
        return;
    }

    if (amount > walletData.balance) {
        showToast('Insufficient balance', 'error');
        return;
    }

    try {
        const response = await fetch('/api/wallet/convert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                amount: amount,
                from_currency: 'DTC',
                to_currency: toCurrency
            })
        });

        if (response.ok) {
            const result = await response.json();
            hideConversionModal();
            showToast(`Conversion started! Order ID: ${result.order_id}`, 'success');
            loadWalletData();
        } else {
            const error = await response.json();
            showToast('Error: ' + error.detail, 'error');
        }
    } catch (error) {
        console.error('Error converting:', error);
        showToast('Network error', 'error');
    }
}

// Make functions globally available
window.loadWalletData = loadWalletData;
window.showSendDTCModal = showSendDTCModal;
window.hideSendDTCModal = hideSendDTCModal;
window.sendDTC = sendDTC;
window.showSendStarsModal = showSendStarsModal;
window.hideSendStarsModal = hideSendStarsModal;
window.updateStarCount = updateStarCount;
window.sendStars = sendStars;
window.claimMiningReward = claimMiningReward;
window.voteBadge = voteBadge;
window.initializeWallet = initializeWallet;
window.switchBlockchainMode = switchBlockchainMode;
window.showConversionModal = showConversionModal;
window.hideConversionModal = hideConversionModal;
window.updateConversionPreview = updateConversionPreview;
window.convertCrypto = convertCrypto;

// Mining progress functions
let miningData = {
    enabled: false,
    hardwareInfo: {},
    estimatedReward: 0,
    powerWarning: false
};

async function loadMiningStatus() {
    try {
        const response = await fetch('/api/wallet/mining-status');
        if (response.ok) {
            miningData = await response.json();
            updateMiningUI();
        }
    } catch (error) {
        console.error('Error loading mining status:', error);
    }
}

function updateMiningUI() {
    // Update hardware info
    if (miningData.hardware_info) {
        document.getElementById('cpu-cores').textContent = miningData.hardware_info.cpu_cores || 'N/A';
        document.getElementById('memory-gb').textContent = `${miningData.hardware_info.memory_gb || 0} GB`;
        document.getElementById('cpu-usage').textContent = `${miningData.hardware_info.cpu_usage || 0}%`;
        document.getElementById('hardware-score').textContent = `${(miningData.hardware_info.hardware_score * 100 || 0).toFixed(1)}%`;
        document.getElementById('estimated-daily').textContent = `${miningData.estimated_daily_reward || 0} DTC/day`;
    }

    // Update mining status
    const miningBtn = document.getElementById('toggle-mining-btn');
    if (miningBtn) {
        miningBtn.textContent = miningData.mining_enabled ? 'Stop Mining' : 'Start Mining';
        miningBtn.className = `btn ${miningData.mining_enabled ? 'btn-danger' : 'btn-success'}`;
    }

    // Show power warning
    const warningEl = document.getElementById('power-warning');
    if (warningEl) {
        warningEl.style.display = miningData.power_consumption_warning ? 'block' : 'none';
    }
}

async function toggleMining() {
    if (!miningData.mining_enabled) {
        // Ask for confirmation before enabling
        if (!confirm('Mining will use your CPU resources. This may affect system performance. Continue?')) {
            return;
        }

        try {
            const response = await fetch('/api/wallet/enable-mining', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_confirmed: true })
            });

            if (response.ok) {
                const result = await response.json();
                miningData.mining_enabled = true;
                updateMiningUI();
                showToast('Mining enabled! ⛏️', 'success');
            } else {
                const error = await response.json();
                showToast('Error: ' + error.detail, 'error');
            }
        } catch (error) {
            console.error('Error enabling mining:', error);
            showToast('Network error', 'error');
        }
    } else {
        // Disable mining
        try {
            const response = await fetch('/api/wallet/disable-mining', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                miningData.mining_enabled = false;
                updateMiningUI();
                showToast('Mining disabled', 'info');
            } else {
                const error = await response.json();
                showToast('Error: ' + error.detail, 'error');
            }
        } catch (error) {
            console.error('Error disabling mining:', error);
            showToast('Network error', 'error');
        }
    }
}

// Show mining modal
function showMiningModal() {
    loadMiningStatus();
    document.getElementById('mining-modal').style.display = 'block';
}

function hideMiningModal() {
    document.getElementById('mining-modal').style.display = 'none';
}

// Make mining functions globally available
window.loadMiningStatus = loadMiningStatus;
window.toggleMining = toggleMining;
window.showMiningModal = showMiningModal;
window.hideMiningModal = hideMiningModal;

console.log('💰 Wallet module loaded');