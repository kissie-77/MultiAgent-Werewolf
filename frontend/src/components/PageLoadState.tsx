import React from "react";
import { Loader2, AlertTriangle, RefreshCw, Inbox } from "lucide-react";
import { motion } from "motion/react";

export type PageLoadStateVariant = "loading" | "error" | "empty";

export interface PageLoadStateProps {
  variant: PageLoadStateVariant;
  /** 加载时的提示文案 */
  loadingText?: string;
  /** 错误信息 */
  errorText?: string;
  /** 空状态描述 */
  emptyText?: string;
  /** 空状态补充说明 */
  emptyHint?: string;
  /** 重试按钮回调（error/empty 状态时显示） */
  onRetry?: () => void;
  /** 重试按钮文案 */
  retryText?: string;
  /** 自定义操作按钮（如返回链接） */
  action?: React.ReactNode;
  /** 最小高度 */
  minHeight?: string;
}

export default function PageLoadState({
  variant,
  loadingText = "加载中...",
  errorText,
  emptyText,
  emptyHint,
  onRetry,
  retryText = "重试",
  action,
  minHeight = "min-h-[60vh]",
}: PageLoadStateProps) {
  if (variant === "loading") {
    return (
      <div className={`${minHeight} flex flex-col items-center justify-center text-zinc-400`}>
        <Loader2 className="w-8 h-8 animate-spin text-yellow-500 mb-3" />
        <span className="font-sans text-xs text-zinc-400">{loadingText}</span>
      </div>
    );
  }

  if (variant === "error") {
    return (
      <div className={`${minHeight} flex flex-col items-center justify-center text-center px-4 max-w-md mx-auto`}>
        <AlertTriangle className="w-12 h-12 text-red-500/80 mb-4" />
        <h3 className="font-serif text-lg tracking-wider mb-2 text-zinc-200">加载失败</h3>
        <p className="text-xs text-zinc-400 mb-6 leading-relaxed">{errorText || "未知错误"}</p>
        <div className="flex items-center gap-3">
          {onRetry && (
            <button
              onClick={onRetry}
              className="flex items-center gap-2 px-5 py-2.5 bg-zinc-900 border border-zinc-800 hover:border-yellow-500 hover:text-yellow-500 text-xs font-sans text-zinc-300 rounded transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" /> {retryText}
            </button>
          )}
          {action}
        </div>
      </div>
    );
  }

  // empty
  return (
    <div className={`${minHeight} flex flex-col items-center justify-center text-center px-4`}>
      <Inbox className="w-12 h-12 text-zinc-600 mb-4" />
      {emptyText && <p className="font-sans text-sm text-zinc-400 mb-1">{emptyText}</p>}
      {emptyHint && <p className="font-sans text-xs text-zinc-500 opacity-60 mb-4">{emptyHint}</p>}
      <div className="flex items-center gap-3">
        {onRetry && (
          <button
            onClick={onRetry}
            className="flex items-center gap-2 px-5 py-2.5 bg-yellow-600/20 text-yellow-500 hover:bg-yellow-600/30 border border-yellow-600/50 rounded text-xs font-mono tracking-widest uppercase transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" /> {retryText}
          </button>
        )}
        {action}
      </div>
    </div>
  );
}
