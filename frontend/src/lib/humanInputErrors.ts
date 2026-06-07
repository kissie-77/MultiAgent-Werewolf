const REJECT_MESSAGES: Record<string, string> = {
  invalid_token: "座位令牌无效，请从开局页重新进入座位链接。",
  no_input_broker: "本局未注册人机输入通道，可能已结束或并非人机模式。",
  expired_or_unknown: "该决策已过期或不存在，请等待下一轮提示。",
  already_consumed: "该决策已提交，请勿重复操作。",
};

export function humanInputRejectMessage(
  rejectCode?: string | null,
  fallback?: string | null,
): string {
  if (rejectCode && REJECT_MESSAGES[rejectCode]) {
    return REJECT_MESSAGES[rejectCode];
  }
  if (fallback?.trim()) return fallback.trim();
  if (rejectCode) return `提交被拒绝（${rejectCode}）`;
  return "提交失败，请重试。";
}
