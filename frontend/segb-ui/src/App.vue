<template>
  <div class="app-shell">
    <AppHeader />
    <div class="app-main">
      <Sidebar class="main-sidebar"/>
      <main class="main-content">
        <router-view />
      </main>
    </div>
    <FooterLogo />
  </div>

</template>

<script setup>
import AppHeader from '@/components/AppHeader.vue'
import Sidebar from '@/components/Sidebar.vue'
import FooterLogo from '@/components/FooterLogo.vue'
</script>
