const nf0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const nf2 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const brl = (v: number) => `R$ ${nf0.format(Math.round(v))}`;
export const brlCentavos = (v: number) => `R$ ${nf2.format(v)}`;

/** R$ 1,5M · R$ 400 mil · R$ 600/dia — o formato curto dos mockups. */
export function capitalCurto(v: number, diaria = false): string {
  if (diaria) return `R$ ${nf0.format(Math.round(v))}/dia`;
  if (v >= 1_000_000) {
    const m = v / 1_000_000;
    return `R$ ${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(m)}M`;
  }
  if (v >= 1000) return `R$ ${nf0.format(Math.round(v / 1000))} mil`;
  return `R$ ${nf0.format(Math.round(v))}`;
}

export const pct = (v: number) => `${Math.round(v * 100)}%`;

export function soDigitos(v: string) {
  return v.replace(/\D/g, "");
}

export function mascaraCpf(v: string) {
  const d = soDigitos(v).slice(0, 11);
  return d
    .replace(/^(\d{3})(\d)/, "$1.$2")
    .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1-$2");
}

export function mascaraCelular(v: string) {
  const d = soDigitos(v).slice(0, 11);
  if (d.length <= 2) return d ? `(${d}` : "";
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

export function mascaraData(v: string) {
  const d = soDigitos(v).slice(0, 8);
  return d.replace(/^(\d{2})(\d)/, "$1/$2").replace(/^(\d{2})\/(\d{2})(\d)/, "$1/$2/$3");
}

/** dd/mm/aaaa -> aaaa-mm-dd, ou null se a data não existir. */
export function dataParaIso(br: string): string | null {
  const m = br.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (!m) return null;
  const [, d, mo, a] = m;
  const dt = new Date(Number(a), Number(mo) - 1, Number(d));
  if (dt.getFullYear() !== Number(a) || dt.getMonth() !== Number(mo) - 1 || dt.getDate() !== Number(d))
    return null;
  return `${a}-${mo}-${d}`;
}

export function idadeDe(iso: string, hoje = new Date()): number {
  const [a, m, d] = iso.split("-").map(Number);
  let idade = hoje.getFullYear() - a;
  if (hoje.getMonth() + 1 < m || (hoje.getMonth() + 1 === m && hoje.getDate() < d)) idade -= 1;
  return idade;
}

export function cpfValido(cpf: string): boolean {
  const d = soDigitos(cpf);
  if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false;
  for (const n of [9, 10]) {
    let soma = 0;
    for (let i = 0; i < n; i++) soma += Number(d[i]) * (n + 1 - i);
    if (Number(d[n]) !== ((soma * 10) % 11) % 10) return false;
  }
  return true;
}

export function mascararCpf(cpf: string) {
  const d = soDigitos(cpf);
  return d.length === 11 ? `***.${d.slice(3, 6)}.${d.slice(6, 9)}-**` : cpf;
}

export function mascararEmail(e: string) {
  const [u, dom] = e.split("@");
  return dom ? `${u.slice(0, Math.min(5, u.length))}****@${dom}` : e;
}

/** "há 3 h", "há 2 dias" — para a fila do backoffice. */
export function haQuanto(iso: string, agora = new Date()): { texto: string; horas: number } {
  const horas = Math.max(0, (agora.getTime() - new Date(iso).getTime()) / 3_600_000);
  if (horas < 1) return { texto: `${Math.max(1, Math.round(horas * 60))} min`, horas };
  if (horas < 48) return { texto: `${Math.floor(horas)} h`, horas };
  return { texto: `${Math.floor(horas / 24)} dias`, horas };
}

export function dataHora(iso: string) {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const nomeSeguradora = (s: string) => s.replace(/\s*\(fictícia\)/i, "");
