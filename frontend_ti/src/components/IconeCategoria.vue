<script setup>
import { FlaskConical, KeyRound, Laptop, LayoutGrid, LifeBuoy, Mail, Package, Printer, Shield, Smartphone, Wifi } from "lucide-vue-next"

defineProps({ nome: String })
const ICONES = {
	"key-round": KeyRound,
	laptop: Laptop,
	printer: Printer,
	mail: Mail,
	wifi: Wifi,
	"layout-grid": LayoutGrid,
	package: Package,
	smartphone: Smartphone,
	"flask-conical": FlaskConical,
	shield: Shield,
	"life-buoy": LifeBuoy,
}
</script>

<template>
	<component :is="ICONES[nome] || LifeBuoy" />
</template>
