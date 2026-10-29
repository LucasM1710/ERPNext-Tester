<script setup>
defineProps({ linhas: { type: Number, default: 4 }, classe: { type: String, default: "h-4" } })
</script>

<template>
	<div class="animate-pulse space-y-3">
		<div v-for="i in linhas" :key="i" class="rounded-lg bg-realce" :class="classe" :style="{ width: `${100 - ((i * 13) % 35)}%` }" />
	</div>
</template>
