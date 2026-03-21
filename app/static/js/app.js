const form = document.getElementById("uploadForm");
const statusEl = document.getElementById("status");
const summaryEl = document.getElementById("summary");
const reportLink = document.getElementById("reportLink");
const demoBtn = document.getElementById("demoBtn");

const runRequest = async (url, payload) => {
  statusEl.textContent = "正在上传并分析，请稍候...";
  summaryEl.textContent = "分析中...";
  reportLink.textContent = "生成中...";
  reportLink.href = "#";

  try {
    const response = await fetch(url, payload);

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "分析失败");
    }

    const data = await response.json();
    summaryEl.textContent = data.summary || "暂无摘要";
    reportLink.textContent = "下载 PDF 报告";
    reportLink.href = data.report_url;
    statusEl.textContent = "分析完成";
  } catch (error) {
    statusEl.textContent = `错误: ${error.message}`;
    summaryEl.textContent = "请检查 CSV 和 API Key 后重试。";
    reportLink.textContent = "暂无报告";
    reportLink.href = "#";
  }
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(form);
  await runRequest("/analyze", { method: "POST", body: formData });
});

demoBtn.addEventListener("click", async () => {
  statusEl.textContent = "正在运行演示，请稍候...";
  summaryEl.textContent = "分析中...";
  reportLink.textContent = "生成中...";
  reportLink.href = "#";
  await runRequest("/demo", { method: "POST" });
});
