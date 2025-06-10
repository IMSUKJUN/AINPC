const chatBox = document.getElementById('chat-box');
const input = document.getElementById('playerInput');
const startBtn = document.getElementById('startBtn');
let conversationActive = true;

function appendMessage(text, sender) {
  const div = document.createElement('div');
  div.className = 'message ' + sender;
  div.innerText = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function startConversation() {
  startBtn.style.display = 'none';
  const res = await fetch("https://your-app-name.onrender.com/npc/generate_question?npc_id=영희");
  const data = await res.json();
  appendMessage(data.question, 'npc');
}

async function sendMessage() {
  if (!conversationActive) return;

  const content = input.value.trim();
  if (!content) return;

  appendMessage(content, 'player');
  input.value = '';

  const res = await fetch("https://your-app-name.onrender.com/npc/respond", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ npc_id: "영희", content: content })
  });

  const data = await res.json();
  const reply = data.npc_reply || "오류가 발생했습니다.";
  appendMessage(reply, 'npc');

  // 종료 조건 예시
  if (reply.includes("이제 말하기 싫어") || reply.includes("그만")) {
    conversationActive = false;
    input.disabled = true;
  }
}

function endConversation() {
  conversationActive = false;
  input.disabled = true;
  appendMessage("대화를 종료했습니다.", 'npc');
}
