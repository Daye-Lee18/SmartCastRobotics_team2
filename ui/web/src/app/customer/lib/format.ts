// 통화/주문번호 포맷 유틸리티.

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("ko-KR").format(amount) + "원";
}

export function generateOrderNumber(): string {
  const year = new Date().getFullYear();
  const seq = Math.floor(Math.random() * 900) + 100;
  return `ORD-${year}-${seq.toString().padStart(3, "0")}`;
}
