<template>
  <section class="welcome-container">
    <h1 class="title">Welcome to the SEGB Knowledge Hub 👋</h1>
    <p class="welcome-subtitle">
      This platform provides transparent and traceable access to the
      <strong>Semantic Ethical Glass Box (SEGB)</strong> registry.
    </p>

    <div class="info-grid">
      <div class="info-card">
        <h3>🧩 Insert Semantic Log</h3>
        <p>
          Register new semantic events in the system.
          Each log is stored with complete metadata and ontological structure for future analysis.
        </p>
      </div>

      <div class="info-card">
        <h3>🔍 View Semantic Logs</h3>
        <p>
          Explore all recorded logs in a clear, searchable format.
          Review details, relationships, and timestamps in one place.
        </p>
      </div>

      <div class="info-card">
        <h3>🔄 View Modifications</h3>
        <p>
          Track structural and content-level changes across semantic data sources.
          Gain visibility into updates and synchronization operations.
        </p>
      </div>

      <div class="info-card">
        <h3>📅 Modifications by Date</h3>
        <p>
          Filter and visualize modifications chronologically to analyze system evolution or activity bursts.
        </p>
      </div>

      <div class="info-card">
        <h3>❓ SPARQL Queries</h3>
        <p>
          Execute SPARQL queries directly against the triple store.
          Ideal for advanced users performing semantic data analysis.
        </p>
      </div>

      <div class="info-card">
        <h3>💬 AI Assistant</h3>
        <p>
          Interact with an integrated AI assistant that can interpret your questions and
          extract insights using RAG-based reasoning over stored knowledge.
        </p>
      </div>
    </div>
  </section>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600&display=swap');

.welcome-container {
  max-width: 60rem;
  margin: 80px auto;
  padding: 2.5rem 3rem;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(6px);
  font-family: 'Montserrat', sans-serif;
}

.welcome-subtitle {
  text-align: center;
  color: #333;
  font-size: 1.1rem;
  margin-bottom: 2rem;
  line-height: 1.6;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1.5rem;
}

.info-card {
  background: #f9fbff;
  border: 1px solid #dbe8f5;
  border-radius: 12px;
  padding: 1.5rem;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.info-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
}

.info-card h3 {
  color: var(--brand-dark);
  font-size: 1.2rem;
  margin-bottom: 0.6rem;
}

.info-card p {
  color: #444;
  line-height: 1.5;
  font-size: 0.95rem;
}
</style>
