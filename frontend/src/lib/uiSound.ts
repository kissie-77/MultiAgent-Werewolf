import { soundManager } from "../audio/soundManager";

/**
 * UI 交互音的薄封装层。把"开合分音"等约定集中在一处，避免散落各组件。
 * 普通点击仍可直接内联 `soundManager.playUi("ui_click")`；此处仅收拢需要语义区分的场景。
 */

/**
 * 折叠类控件的开/合提示音。
 * @param open 切换后的下一个 open 状态：true=展开 → ui_panel_open；false=收起 → ui_panel_close。
 */
export function playToggle(open: boolean): void {
  soundManager.playUi(open ? "ui_panel_open" : "ui_panel_close");
}
