// Duas páginas com o mesmo app:
// - /consulta: dados reais da empresa (Equipamentos, OS Interna/Externa), só leitura;
// - /cliente: portal completo, com os DocTypes próprios do portal.
export const MODO = location.pathname.startsWith("/consulta") ? "consulta" : "completo"
export const BASE = MODO === "consulta" ? "/consulta/" : "/cliente/"
export const CONSULTA = MODO === "consulta"
