<script setup>
import { BarChart, CustomChart, GaugeChart, LineChart, PieChart, ScatterChart } from "echarts/charts"
import { GridComponent, LegendComponent, MarkAreaComponent, MarkLineComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import VChart from "vue-echarts"

use([
	CanvasRenderer,
	BarChart,
	LineChart,
	PieChart,
	GaugeChart,
	ScatterChart,
	CustomChart,
	GridComponent,
	TooltipComponent,
	LegendComponent,
	MarkAreaComponent,
	MarkLineComponent,
])

defineProps({ opcoes: { type: Object, required: true }, altura: { type: String, default: "260px" } })
</script>

<template>
	<VChart :option="opcoes" :style="{ height: altura }" autoresize />
</template>
