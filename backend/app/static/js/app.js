// เริ่มต้นการทำงานเมื่อ DOM โหลดเสร็จ
document.addEventListener("DOMContentLoaded", () => {
    console.log("🔹 DOM Loaded");
    setupCreateAgentForm();
    setupWebhookHandlers();
    setupEditAgentForm();
    loadAgentsList(); // เรียกฟังก์ชันโหลด AI Agents เมื่อโหลดหน้า
});

// ฟังก์ชันสำหรับจัดการฟอร์มสร้าง Agent
function setupCreateAgentForm() {
    const form = document.getElementById("createAgentForm");
    if (!form) {
        console.log("❌ ไม่พบฟอร์ม createAgentForm");
        return;
    }
    form.addEventListener("submit", handleCreateAgentSubmit);
}

// ฟังก์ชันจัดการการส่งฟอร์ม
async function handleCreateAgentSubmit(event) {
    event.preventDefault();
    console.log("🔹 Form submitted");

    const formData = {
        agent_name: document.getElementById("agent_name")?.value?.trim() || "",
        agent_type: document.getElementById("agent_type")?.value || "",
        prompt_template: document.getElementById("prompt_template")?.value?.trim() || ""
    };

    console.log("🔹 Form Data:", formData);

    if (!formData.agent_name || !formData.agent_type || !formData.prompt_template) {
        alert("❌ กรุณากรอกข้อมูลให้ครบทุกช่อง");
        return;
    }

    try {
        const response = await fetch("/api/agents/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formData)
        });

        const data = await response.json();
        console.log("✅ Response:", data);

        if (data.message) {
            alert("✅ " + data.message);
            setTimeout(() => window.location.href = "/", 2000);
        } else {
            alert("❌ " + data.error);
        }
    } catch (error) {
        console.error("❌ Error:", error);
        alert("❌ เกิดข้อผิดพลาดในการส่งข้อมูล");
    }
}

// ฟังก์ชันสำหรับจัดการฟอร์มแก้ไข Agent
function setupEditAgentForm() {
    const form = document.getElementById("editAgentForm");
    if (form) {
        form.addEventListener("submit", function(event) {
            event.preventDefault();
            const agentId = form.getAttribute("data-agent-id");
            handleEditAgentSubmit(event, agentId);
        });
    }
}

// ฟังก์ชันจัดการการแก้ไข Agent
async function handleEditAgentSubmit(event, agentId) {
    event.preventDefault();
    
    const formData = {
        agent_name: document.getElementById("agent_name")?.value?.trim() || "",
        agent_type: document.getElementById("agent_type")?.value || "",
        prompt_template: document.getElementById("prompt_template")?.value?.trim() || ""
    };

    if (!formData.agent_name || !formData.agent_type || !formData.prompt_template) {
        alert("❌ กรุณากรอกข้อมูลให้ครบทุกช่อง");
        return;
    }

    try {
        const response = await fetch(`/api/agents/update/${agentId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (data.message) {
            alert("✅ " + data.message);
            window.location.href = "/";
        } else {
            alert("❌ " + data.error);
        }
    } catch (error) {
        console.error("❌ Error:", error);
        alert("❌ เกิดข้อผิดพลาดในการแก้ไขข้อมูล");
    }
}

// ฟังก์ชันลบ Agent
function deleteAgent(agentId) {
    console.log("🔹 กำลังลบ Agent:", agentId);
    
    if (!confirm("⚠️ คุณแน่ใจหรือไม่ว่าต้องการลบ Agent นี้?")) {
        return;
    }

    fetch(`/api/agents/delete/${agentId}`, {
        method: "DELETE"
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("เกิดข้อผิดพลาดในการลบ Agent");
        }
        return response.json();
    })
    .then(data => {
        console.log("✅ ผลการลบ:", data);
        alert("✅ ลบ Agent สำเร็จ!");
        location.reload();
    })
    .catch(error => {
        console.error("❌ เกิดข้อผิดพลาด:", error);
        alert("❌ เกิดข้อผิดพลาด: " + error.message);
    });
}

// แยกฟังก์ชันสำหรับจัดการ Webhook
function setupWebhookHandlers() {
    const webhookForm = document.getElementById("webhookForm");
    if (webhookForm) {
        webhookForm.addEventListener("submit", handleWebhookSubmit);
    }
}

// ฟังก์ชันสำหรับจัดการการสร้าง Webhook
async function handleWebhookSubmit(event) {
    event.preventDefault();
    console.log("🔹 กำลังสร้าง Webhook");

    const agency_name = document.getElementById("agency_name")?.value?.trim() || "";
    const sub_agent = document.getElementById("sub_agent")?.value?.trim() || "";
    const loadingOverlay = document.getElementById("loadingOverlay");
    const successDialog = document.getElementById("successDialog");
    const webhookUrlInput = document.getElementById("webhookUrl");

    if (!agency_name || !sub_agent) {
        showAlert("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน");
        return;
    }

    try {
        loadingOverlay.classList.remove("hidden");
        loadingOverlay.classList.add("flex");

        const response = await fetch('/api/webhooks/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                agency_name,
                sub_agent
            })
        });

        const data = await response.json();
        console.log("✅ ผลการสร้าง Webhook:", data);

        if (response.ok) {
            loadingOverlay.classList.add("hidden");
            loadingOverlay.classList.remove("flex");

            // แสดง Success Dialog พร้อม Webhook URL
            webhookUrlInput.value = window.location.origin + data.webhook_url;
            successDialog.classList.remove("hidden");
            successDialog.classList.add("flex");
        } else {
            throw new Error(data.error || "เกิดข้อผิดพลาดในการสร้าง Webhook");
        }
    } catch (error) {
        console.error("❌ เกิดข้อผิดพลาด:", error);
        showAlert("❌ " + error.message);
        
        loadingOverlay.classList.add("hidden");
        loadingOverlay.classList.remove("flex");
    }
}

// ฟังก์ชันโหลดรายการ AI Agents
async function loadAgentsList() {
    try {
        const response = await fetch('/api/agents'); // ✅ ใช้ API ที่ถูกต้อง
        const agents = await response.json();

        console.log("✅ AI Agents Loaded:", agents);

        const selectElement = document.getElementById('sub_agent');
        if (!selectElement) {
            console.error("❌ ไม่พบ element sub_agent");
            return;
        }

        // เคลียร์ตัวเลือกเดิม
        selectElement.innerHTML = '<option value="">เลือก AI Agent</option>';

        // เพิ่มตัวเลือกใหม่
        agents.forEach(agent => {
            const option = document.createElement('option');
            option.value = agent.agent_name; // ✅ ใช้ชื่อ Agent เป็นค่า
            option.textContent = agent.agent_name;
            selectElement.appendChild(option);
        });

    } catch (error) {
        console.error("❌ เกิดข้อผิดพลาดในการโหลดรายการ AI Agents:", error);
        showAlert("❌ เกิดข้อผิดพลาดในการโหลดรายการ AI Agents");
    }
}

// ฟังก์ชันลบ Webhook
function deleteWebhook(webhookId) {
    if (!confirm("⚠️ คุณแน่ใจหรือไม่ว่าต้องการลบ Webhook นี้?")) {
        return;
    }

    fetch(`/api/webhooks/delete/${webhookId}`, {
        method: "DELETE"
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("เกิดข้อผิดพลาดในการลบ Webhook");
        }
        return response.json();
    })
    .then(data => {
        console.log("✅ ผลการลบ:", data);
        alert("✅ ลบ Webhook สำเร็จ!");
        location.reload();
    })
    .catch(error => {
        console.error("❌ เกิดข้อผิดพลาด:", error);
        alert("❌ เกิดข้อผิดพลาด: " + error.message);
    });
}

// ฟังก์ชันเปิด/ปิดการทำงานของ Webhook
function toggleWebhookStatus(webhookId, currentStatus) {
    fetch(`/api/webhooks/toggle/${webhookId}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            is_active: !currentStatus
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("เกิดข้อผิดพลาดในการเปลี่ยนสถานะ Webhook");
        }
        return response.json();
    })
    .then(data => {
        console.log("✅ ผลการเปลี่ยนสถานะ:", data);
        location.reload();
    })
    .catch(error => {
        console.error("❌ เกิดข้อผิดพลาด:", error);
        alert("❌ เกิดข้อผิดพลาด: " + error.message);
    });
}

// ฟังก์ชันคัดลอก Webhook URL
function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
        .then(() => {
            alert("✅ คัดลอก Webhook URL แล้ว");
        })
        .catch(error => {
            console.error("❌ เกิดข้อผิดพลาดในการคัดลอก:", error);
            alert("❌ ไม่สามารถคัดลอก URL ได้");
        });
}

// ฟังก์ชันคัดลอก Webhook URL
function copyWebhookUrl() {
    const webhookUrl = document.getElementById("webhookUrl");
    webhookUrl.select();
    document.execCommand('copy');
    showAlert("✅ คัดลอก Webhook URL แล้ว");
}

// ฟังก์ชันปิด Success Dialog
function closeSuccessDialog() {
    const successDialog = document.getElementById("successDialog");
    successDialog.classList.add("hidden");
    successDialog.classList.remove("flex");
    window.location.href = "/";  // กลับไปหน้า dashboard
}

// ฟังก์ชันแสดง Alert
function showAlert(message) {
    const alert = document.getElementById("alert");
    const alertMessage = document.getElementById("alertMessage");
    
    alertMessage.textContent = message;
    alert.classList.remove("hidden");
    alert.classList.add("flex");
    
    setTimeout(() => {
        alert.classList.add("hidden");
        alert.classList.remove("flex");
    }, 3000);
}

// ฟังก์ชันสำหรับ generate webhook URL
async function generateWebhookUrl() {
    try {
        const response = await fetch('/generate_webhook_url');
        const data = await response.json();
        const webhookInput = document.getElementById("webhook_url");
        if (webhookInput) {
            webhookInput.value = data.webhook_url;
        }
    } catch (error) {
        console.error("❌ Error generating webhook URL:", error);
        alert("❌ เกิดข้อผิดพลาดในการสร้าง Webhook URL");
    }
}

// ฟังก์ชันสำหรับคัดลอก webhook URL
async function copyWebhookUrl() {
    const webhookInput = document.getElementById("webhook_url");
    if (webhookInput?.value) {
        try {
            await navigator.clipboard.writeText(webhookInput.value);
            alert("✅ คัดลอก Webhook URL สำเร็จ!");
        } catch (error) {
            console.error("❌ Error copying webhook URL:", error);
            alert("❌ เกิดข้อผิดพลาดในการคัดลอก URL");
        }
    }
}
