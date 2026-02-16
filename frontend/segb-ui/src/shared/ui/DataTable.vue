<template>
  <div class="table-wrap" :style="tableWrapStyle">
    <table>
      <thead>
        <tr>
          <th v-for="column in columns" :key="column.key">{{ column.label }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="rows.length === 0">
          <td :colspan="columns.length" class="empty">No rows.</td>
        </tr>
        <tr v-for="(row, index) in rows" :key="index">
          <td v-for="column in columns" :key="column.key">{{ row[column.key] ?? '' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export type TableColumn = {
  key: string
  label: string
}

const props = defineProps<{
  columns: TableColumn[]
  rows: Array<Record<string, string | number | null | undefined>>
  maxHeight?: string | number
}>()

const tableWrapStyle = computed(() => {
  if (props.maxHeight === undefined || props.maxHeight === null) {
    return undefined
  }
  return {
    maxHeight: typeof props.maxHeight === 'number' ? `${props.maxHeight}px` : props.maxHeight,
  }
})
</script>

<style scoped>
.table-wrap {
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 520px;
}

th,
td {
  text-align: left;
  border-bottom: 1px solid var(--border-muted);
  padding: 0.62rem 0.7rem;
  font-size: 0.9rem;
}

th {
  background: var(--surface-alt);
  color: var(--ink-700);
  font-weight: 650;
  position: sticky;
  top: 0;
}

td {
  color: var(--ink-900);
  white-space: pre-line;
}

.empty {
  text-align: center;
  color: var(--ink-500);
  padding: 1rem;
}
</style>
