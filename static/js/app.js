console.log("🔹 app.js loaded successfully");

// แยกฟังก์ชันสำหรับจัดการฟอร์มสร้าง Agent
function setupCreateAgentForm() {
    const form = document.getElementById("createAgentForm");
    if (!form) {
        console.log("❌ ไม่พบฟอร์ม createAgentForm");
        return;
    }

    form.addEventListener("submit", handleCreateAgentSubmit);
}

// ฟังก์ชันจัดการการส่งฟอร์ม
function handleCreateAgentSubmit(event) {
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

    fetch("/api/agents/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        console.log("✅ Response:", data);
        if (data.message) {
            alert("✅ " + data.message);
            setTimeout(() => window.location.href = "/", 2000);
        } else {
            alert("❌ " + data.error);
        }
    })
    .catch(error => {
        console.error("❌ Error:", error);
        alert("❌ เกิดข้อผิดพลาดในการส่งข้อมูล");
    });
}

// แยกฟังก์ชันสำหรับจัดการ Webhook
function setupWebhookHandlers() {
    const webhookForm = document.getElementById("webhookForm");
    if (webhookForm) {
        webhookForm.addEventListener("submit", handleWebhookSubmit);
    }
}

async function handleWebhookSubmit(event) {
    event.preventDefault();
    const agency_name = document.getElementById("agency_name")?.value?.trim() || "";
    const webhook_url = document.getElementById("webhook_url")?.value?.trim() || "";
    const sub_agent = document.getElementById("sub_agent")?.value?.trim() || "";
    const result = document.getElementById("webhook_result");

    if (!agency_name || !webhook_url) {
        if (result) {
            result.textContent = "⚠️ กรุณากรอกข้อมูลให้ครบ";
            result.classList.add("text-red-500");
        }
        return;
    }

    try {
        const response = await fetch('/api/webhooks/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agency_name, webhook_url, sub_agent })
        });

        const data = await response.json();
        
        if (result) {
            if (response.ok) {
                result.textContent = "✅ Webhook สร้างสำเร็จ!";
                result.classList.add("text-green-500");
            } else {
                result.textContent = `❌ Error: ${data.error}`;
                result.classList.add("text-red-500");
            }
        }
    } catch (error) {
        console.error("❌ Error:", error);
        if (result) {
            result.textContent = "❌ เกิดข้อผิดพลาดในการสร้าง Webhook";
            result.classList.add("text-red-500");
        }
    }
}

// เริ่มต้นการทำงานเมื่อ DOM โหลดเสร็จ
document.addEventListener("DOMContentLoaded", () => {
    console.log("🔹 DOM Loaded");
    setupCreateAgentForm();
    setupWebhookHandlers();
});

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
