import React, { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import { Key, Loader2, Settings } from "lucide-react";
import { ApiClient } from "../api/client";
import type {
  ApiKeysStatusResponse,
  ProviderFieldSchema,
  ProviderSchema,
} from "../api/types";

interface ApiKeysSettingsModalProps {
  open: boolean;
  onClose: () => void;
}

export default function ApiKeysSettingsModal({ open, onClose }: ApiKeysSettingsModalProps) {
  const [providers, setProviders] = useState<ProviderSchema[]>([]);
  const [status, setStatus] = useState<ApiKeysStatusResponse | null>(null);
  const [selectedProviderId, setSelectedProviderId] = useState("doubao");
  const [draftFields, setDraftFields] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const selectedProvider = providers.find((p) => p.provider_id === selectedProviderId);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [providerList, keyStatus] = await Promise.all([
        ApiClient.getProviders(),
        ApiClient.getApiKeysStatus(),
      ]);
      setProviders(providerList.providers);
      setStatus(keyStatus);
      const defaultId =
        providerList.providers.find((p) => p.provider_id === providerList.default_provider_id)
          ?.provider_id ?? providerList.providers[0]?.provider_id ?? "doubao";
      setSelectedProviderId((prev) =>
        providerList.providers.some((p) => p.provider_id === prev) ? prev : defaultId
      );
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(
        msg.includes("Failed to fetch") || msg.includes("NetworkError")
          ? "无法连接后端 API。请先在仓库根目录运行：uv run werewolf-api --port 8010"
          : msg
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    setDraftFields({});
    setSaveMessage(null);
    void loadSettings();
  }, [open, loadSettings]);

  const fieldStatus = (field: ProviderFieldSchema) =>
    status?.env_fields?.[field.env_name];

  const handleFieldChange = (envName: string, value: string) => {
    setDraftFields((prev) => ({ ...prev, [envName]: value }));
    setSaveMessage(null);
  };

  const handleSave = async () => {
    if (!selectedProvider) return;
    const updates: Record<string, string> = {};
    for (const field of selectedProvider.fields) {
      const draft = draftFields[field.env_name];
      if (draft !== undefined && draft.trim()) {
        updates[field.env_name] = draft.trim();
      }
    }
    if (Object.keys(updates).length === 0) {
      setError("请至少填写一个字段再保存");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await ApiClient.updateApiKeys({ fields: updates });
      setSaveMessage(`已写入 ${res.updated_env_names.join("、")}`);
      setDraftFields({});
      const keyStatus = await ApiClient.getApiKeysStatus();
      setStatus(keyStatus);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const renderField = (field: ProviderFieldSchema) => {
    const configured = fieldStatus(field);
    const draft = draftFields[field.env_name];
    const placeholder = field.example || field.description || field.label;
    return (
      <div key={field.env_name} className="flex flex-col gap-2">
        <label className="font-sans text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center justify-between gap-2">
          <span className="flex items-center gap-2">
            <Key className="w-3.5 h-3.5 text-amber-500/80" />
            {field.label}
            <span className="text-zinc-600 font-mono normal-case">{field.env_name}</span>
          </span>
          {configured?.configured && !draft && (
            <span className="text-emerald-500/80 font-mono text-[9px] normal-case">
              已配置 {configured.masked ? `(${configured.masked})` : ""}
            </span>
          )}
        </label>
        <div className="flex items-center gap-2 bg-black/60 border border-slate-800 hover:border-amber-900/50 focus-within:border-amber-500/50 focus-within:bg-black/80 p-2 rounded transition-colors shadow-inner">
          <input
            type={field.secret ? "password" : "text"}
            placeholder={placeholder}
            value={draft ?? ""}
            onChange={(e) => handleFieldChange(field.env_name, e.target.value)}
            className="bg-transparent border-none outline-none font-mono text-amber-100 text-xs flex-grow w-full placeholder:text-slate-700"
          />
        </div>
        {field.description && (
          <p className="text-[9px] text-slate-500 leading-relaxed font-sans pl-1">{field.description}</p>
        )}
      </div>
    );
  };

  if (!open) return null;

  return createPortal(
    <AnimatePresence>
      {open && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-md p-4 select-none"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            onClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
            className="w-full max-w-lg bg-slate-950 bg-woodcut-dark border border-amber-900/40 p-6 md:p-8 rounded-xl relative shadow-[0_0_50px_rgba(0,0,0,0.8)] overflow-hidden"
          >
            <div className="absolute top-2 left-2 w-3 h-3 border-t border-l border-amber-600/40" />
            <div className="absolute top-2 right-2 w-3 h-3 border-t border-r border-amber-600/40" />
            <div className="absolute bottom-2 left-2 w-3 h-3 border-b border-l border-amber-600/40" />
            <div className="absolute bottom-2 right-2 w-3 h-3 border-b border-r border-amber-600/40" />

            <button
              type="button"
              onClick={onClose}
              onMouseDown={(e) => e.stopPropagation()}
              className="absolute top-4 right-4 z-50 text-slate-500 hover:text-amber-500 transition-colors p-1"
            >
              ✕
            </button>

            <h2 className="text-lg font-serif font-black text-amber-500 uppercase tracking-widest mb-2 border-b border-amber-900/30 pb-3 flex items-center gap-2 relative z-10 drop-shadow-md">
              <Settings className="w-5 h-5 text-amber-600" />
              枢纽引擎 ∙ 密钥档案
            </h2>
            <p className="text-[10px] text-slate-500 font-sans mb-4 relative z-10">
              按供应商写入服务端 <span className="font-mono text-zinc-400">.env</span>
              {status?.env_file ? ` (${status.env_file})` : ""}
              {!status?.writable && status !== null && (
                <span className="text-red-400 block mt-1">当前环境不可写，请手动编辑 .env</span>
              )}
            </p>

            {loading ? (
              <div className="flex items-center justify-center gap-2 py-12 text-zinc-500">
                <Loader2 className="w-5 h-5 animate-spin text-amber-500" />
                <span className="font-sans text-xs">加载供应商配置…</span>
              </div>
            ) : error && providers.length === 0 ? (
              <div className="py-8 text-center text-red-400/90 text-xs font-sans">{error}</div>
            ) : (
              <div className="flex flex-col gap-5 max-h-[60vh] overflow-y-auto pr-2 custom-scrollbar relative z-10">
                <div className="flex flex-col gap-2">
                  <label className="font-sans text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                    选择供应商
                  </label>
                  <select
                    value={selectedProviderId}
                    onChange={(e) => {
                      setSelectedProviderId(e.target.value);
                      setDraftFields({});
                      setSaveMessage(null);
                    }}
                    className="bg-black/60 border border-slate-800 text-amber-100 text-xs font-sans px-3 py-2 rounded outline-none focus:border-amber-500/50"
                  >
                    {providers.map((p) => (
                      <option key={p.provider_id} value={p.provider_id}>
                        {p.display_name}
                      </option>
                    ))}
                  </select>
                </div>

                {selectedProvider?.fields.map(renderField)}

                <p className="text-[10px] text-slate-500 leading-relaxed font-sans mt-1 border-l-2 border-amber-900/50 pl-3">
                  模型展示名可在 .env 中设置 <span className="font-mono">ARK_EP_DISPLAY</span>、
                  <span className="font-sans"> DEEPSEEK_MODEL_DISPLAY</span> 等，避免界面显示 ep- 编号。
                </p>

                {error && providers.length > 0 && (
                  <p className="text-[10px] text-red-400 font-sans">{error}</p>
                )}
                {saveMessage && (
                  <p className="text-[10px] text-emerald-400 font-sans">{saveMessage}</p>
                )}
              </div>
            )}

            <div className="mt-6 pt-4 border-t border-amber-900/30 flex justify-end gap-3 relative z-10">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-zinc-400 hover:text-zinc-200 font-sans text-xs"
              >
                关闭
              </button>
              <button
                type="button"
                onClick={() => void handleSave()}
                disabled={saving || loading || status?.writable === false}
                className="px-6 py-2.5 bg-amber-950/40 border border-amber-600/50 text-amber-500 font-sans font-black text-xs uppercase tracking-widest hover:bg-amber-900/60 hover:text-amber-400 transition-all rounded disabled:opacity-40"
              >
                {saving ? "写入中…" : "铭刻至 .env"}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body
  );
}
