<script setup>
import { BatteryCharging, HardDrive, Keyboard, Laptop, Monitor, Mouse, Package, Printer, Router, Server, Smartphone } from "lucide-vue-next"

defineProps({ nome: String })
const ICONES = {
	laptop: Laptop,
	monitor: Monitor,
	printer: Printer,
	smartphone: Smartphone,
	server: Server,
	router: Router,
	"hard-drive": HardDrive,
	keyboard: Keyboard,
	mouse: Mouse,
	"battery-charging": BatteryCharging,
	package: Package,
}
</script>

<template>
	<component :is="ICONES[nome] || Package" />
</template>
