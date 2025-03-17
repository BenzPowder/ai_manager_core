// ฟังก์ชันสำหรับแสดง loading overlay
function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
}

// ฟังก์ชันสำหรับซ่อน loading overlay
function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

// ฟังก์ชันสำหรับแสดง alert
function showAlert(message, isError = false) {
    const alert = document.getElementById('alert');
    const alertMessage = document.getElementById('alertMessage');
    const alertIcon = document.getElementById('alertIcon');
    
    if (alert && alertMessage && alertIcon) {
        alert.style.display = 'block';
        alertMessage.textContent = message;
        
        if (isError) {
            alert.querySelector('div').classList.add('bg-red-100');
            alertMessage.classList.add('text-red-600');
            alertIcon.classList.add('fa-exclamation-circle', 'text-red-600');
        } else {
            alert.querySelector('div').classList.add('bg-green-100');
            alertMessage.classList.add('text-green-600');
            alertIcon.classList.add('fa-check-circle', 'text-green-600');
        }
        
        // ซ่อน alert หลังจาก 3 วินาที
        setTimeout(() => {
            alert.style.display = 'none';
        }, 3000);
    }
}

// ฟังก์ชันสำหรับแสดง success dialog
function showSuccessDialog(webhookUrl) {
    const dialog = document.getElementById('successDialog');
    const urlInput = document.getElementById('webhookUrl');
    
    if (dialog && urlInput) {
        dialog.style.display = 'flex';
        urlInput.value = webhookUrl;
    }
}

// ฟังก์ชันสำหรับปิด success dialog
function closeSuccessDialog() {
    const dialog = document.getElementById('successDialog');
    if (dialog) {
        dialog.style.display = 'none';
    }
}

// ฟังก์ชันสำหรับคัดลอก webhook URL
function copyWebhookUrl() {
    const urlInput = document.getElementById('webhookUrl');
    if (urlInput) {
        urlInput.select();
        document.execCommand('copy');
        showAlert('คัดลอก URL สำเร็จ');
    }
}

// โหลดรายการ AI Agents สำหรับ webhook form
async function loadAgents() {
    try {
        const response = await fetch('/api/agents');
        const agents = await response.json();
        
        const select = document.getElementById('sub_agent');
        if (select) {
            agents.forEach(agent => {
                const option = document.createElement('option');
                option.value = agent.name;
                option.textContent = agent.name;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading agents:', error);
        showAlert('ไม่สามารถโหลดรายการ AI Agents ได้', true);
    }
}

// เมื่อโหลดหน้าเว็บเสร็จ
document.addEventListener('DOMContentLoaded', () => {
    // โหลด agents สำหรับ webhook form
    if (window.location.pathname === '/create_webhook') {
        loadAgents();
    }
    
    // จัดการ form สำหรับสร้าง agent
    const createAgentForm = document.getElementById('createAgentForm');
    if (createAgentForm) {
        createAgentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            showLoading();
            
            try {
                const formData = {
                    name: document.getElementById('name').value,
                    description: document.getElementById('description').value,
                    prompt_template: document.getElementById('prompt_template').value
                };
                
                const response = await fetch('/api/agents/create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showAlert('สร้าง Agent สำเร็จ');
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 2000);
                } else {
                    throw new Error(result.error || 'ไม่สามารถสร้าง Agent ได้');
                }
            } catch (error) {
                console.error('Error creating agent:', error);
                showAlert(error.message, true);
            } finally {
                hideLoading();
            }
        });
    }
    
    // จัดการ form สำหรับสร้าง webhook
    const createWebhookForm = document.getElementById('createWebhookForm');
    if (createWebhookForm) {
        createWebhookForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            showLoading();
            
            try {
                const formData = {
                    agency_name: document.getElementById('agency_name').value,
                    sub_agent: document.getElementById('sub_agent').value
                };
                
                const response = await fetch('/api/webhooks/create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showSuccessDialog(result.webhook_url);
                } else {
                    throw new Error(result.error || 'ไม่สามารถสร้าง Webhook ได้');
                }
            } catch (error) {
                console.error('Error creating webhook:', error);
                showAlert(error.message, true);
            } finally {
                hideLoading();
            }
        });
    }
});
