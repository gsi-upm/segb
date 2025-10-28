<template>
    <aside class="sidebar panel">
        <RouterLink class="link" :to="{ name: 'insert' }">➕ Insert Semantic Log</RouterLink>
        <RouterLink class="link" :to="{ name: 'view' }">🔍 View Semantic Logs</RouterLink>
        <RouterLink class="link" :to="{ name: 'mods' }">🔄 View Modifications</RouterLink>
        <RouterLink class="link" :to="{ name: 'modsByDate' }">📅 View Mods by Date</RouterLink>
        <RouterLink class="link" :to="{ name: 'query' }">❓ Run SPARQL Query</RouterLink>
        <!-- <RouterLink class="link" :to="{ name: 'rag' }">『💬』AI Assistant</RouterLink> -->
    </aside>
</template>

<script setup></script>

<style scoped>

.sidebar {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    padding: 2.25rem;
}

.link {
    display: block;
    padding: .8rem 1rem;
    background: #fff;
    border-radius: 8px;
    border: 1px solid #ddd;
    text-decoration: none;
    color: #000;
    font-family: 'Montserrat', sans-serif;
    font-weight: 600
}



</style>