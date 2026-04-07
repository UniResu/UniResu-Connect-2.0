const topics = [
  { title: "Estudos Qualitativos e Quantitativos", author: "Matheus G.", replies: 4, views: 42 },
  { title: "Tipos de Estudos de Caso", author: "Juliana M.", replies: 2, views: 28 },
  { title: "Como iniciar uma pesquisa acadêmica?", author: "Luan D.", replies: 7, views: 80 },
];

const topicsList = document.getElementById("topicsList");
const searchInput = document.getElementById("searchInput");

function renderTopics(list) {
  topicsList.innerHTML = "";
  list.forEach(t => {
    const topic = document.createElement("div");
    topic.classList.add("topic");
    topic.innerHTML = `
      <h3>${t.title}</h3>
      <p><strong>Autor:</strong> ${t.author} — ${t.replies} respostas · ${t.views} visualizações</p>
    `;
    topicsList.appendChild(topic);
  });
}

renderTopics(topics);

searchInput.addEventListener("input", (e) => {
  const value = e.target.value.toLowerCase();
  const filtered = topics.filter(t => t.title.toLowerCase().includes(value));
  renderTopics(filtered);
});

document.getElementById("newTopicBtn").addEventListener("click", () => {
  const title = prompt("Título do novo tópico:");
  if (title) {
    topics.push({ title, author: "Você", replies: 0, views: 1 });
    renderTopics(topics);
  }
});