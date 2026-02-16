<template>
  <p :class="['banner', tone]">{{ message }}</p>
</template>

<script setup lang="ts">
defineProps<{
  message: string
  tone?: 'info' | 'success' | 'warning' | 'error'
}>()
</script>

<style scoped>
.banner {
  border-radius: 10px;
  padding: 0.7rem 0.85rem;
  font-size: 0.9rem;
  border: 1px solid transparent;
}

.info {
  background: #e8f6fe;
  color: #005f91;
  border-color: #9fd7f1;
}

.success {
  background: #e4f4fd;
  color: #005b89;
  border-color: #8ccfee;
}

.warning {
  background: #fffbeb;
  color: #92400e;
  border-color: #fde68a;
}

.error {
  background: #fef2f2;
  color: #991b1b;
  border-color: #fecaca;
}
</style>
