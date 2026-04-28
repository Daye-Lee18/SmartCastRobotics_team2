// 이메일 검증 (Step 4 주문자 정보).
//
// 실용적인 이메일 정규식:
//   - 로컬 파트: @/공백 제외 1자 이상
//   - @ 1 개
//   - 도메인: @/공백/쩜 제외 1자 이상 + "." + 2자 이상 TLD
//   - 연속 점(..) 금지, 점으로 시작/끝 금지
// RFC 5322 완벽 호환은 아니지만 99% 실 사용 케이스를 잡는다.

const EMAIL_REGEX =
  /^(?!\.)(?!.*\.\.)[^\s@.]+(?:\.[^\s@.]+)*@[^\s@.]+(?:\.[^\s@.]+)*\.[^\s@.]{2,}$/;

/** 이메일 형식이 유효한지 검사 (공백 자동 trim). */
export function isValidEmail(value: string): boolean {
  const trimmed = value.trim();
  if (trimmed.length === 0) return false;
  if (trimmed.length > 254) return false; // RFC 5321 권장 상한
  return EMAIL_REGEX.test(trimmed);
}

/** 사용자 친화적인 이메일 에러 메시지. 빈 값은 "필수" 아닌 "형식" 메시지만 담당. */
export function emailErrorMessage(value: string): string | null {
  const trimmed = value.trim();
  if (trimmed.length === 0) return null; // 필수 검사와 분리
  if (!trimmed.includes("@")) return "이메일에 '@' 가 포함되어야 합니다.";
  const [local, domain] = trimmed.split("@");
  if (!local) return "'@' 앞에 사용자 이름이 필요합니다.";
  if (!domain) return "'@' 뒤에 도메인이 필요합니다.";
  if (!domain.includes(".")) return "도메인에 '.' 이 포함되어야 합니다 (예: gmail.com).";
  if (trimmed.length > 254) return "이메일이 너무 깁니다 (254자 이하).";
  if (!EMAIL_REGEX.test(trimmed)) return "올바른 이메일 주소 형식이 아닙니다.";
  return null;
}
