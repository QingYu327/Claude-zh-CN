// ============================================================================
//  睡醒的夜猫子 · Claude 主界面汉化预加载 (injected into mainView.js + claudePagePreview.js)
//  作用：claude.ai 主聊天界面是远程加载的网页，本地 i18n 包不影响它。
//  主视图（Ri.CLAUDE_AI_WEB）的 preload 是 .vite/build/mainView.js（2026-09-18 实锤），
//  claudePagePreview.js 只负责预览标签页。两个都注入。
//  这里在【主 webview 的 preload】里用 MutationObserver 持续把可见英文 UI
//  文本替换为中文（仅匹配白名单，绝不翻译 AI 回复正文）。
// ============================================================================
(function () {
  'use strict';
  if (window.__claudeZhCnPreload) return;
  window.__claudeZhCnPreload = true;

  var MAP = {
    // ---- 侧边栏 / 导航 ----
    "New chat": "新建对话",
    "New Chat": "新建对话",
    "New": "新建",
    "Artifacts": "工件",
    "Free plan": "免费套餐",
    "Get help": "获取帮助",
    "Get apps and extensions": "获取应用与扩展",
    "Upgrade plan": "升级套餐",
    "Learn": "学习",
    "Write": "写作",
    "Code": "代码",
    "Life stuff": "生活琐事",
    "Claude's choice": "让 Claude 选",
    "Search chats": "搜索对话",
    "Search Chats": "搜索对话",
    "Search": "搜索",
    "Projects": "项目",
    "Chats": "对话",
    "Starred": "已收藏",
    "Archive": "归档",
    "Archived": "已归档",
    "Trash": "回收站",
    "Files": "文件",
    "Shared": "已分享",
    "Styles": "风格",
    "Settings": "设置",
    "Profile": "个人资料",
    "Help": "帮助",
    "Log out": "退出登录",
    "Log Out": "退出登录",
    "Sign out": "退出登录",
    "Sign Out": "退出登录",
    "Upgrade": "升级",
    "Upgrade plan": "升级套餐",
    "Learn": "了解更多",
    "Learn more": "了解更多",
    "Customize": "自定义",
    "Customize Claude": "自定义 Claude",
    "Invite": "邀请",
    "Feedback": "反馈",
    "Contact": "联系",
    "About": "关于",
    "What's new": "新功能",
    "Download": "下载",
    "Print": "打印",
    "Theme": "主题",
    "Appearance": "外观",
    "Language": "语言",
    // ---- 输入区 / Composer ----
    "How can I help": "有什么可以帮您？",
    "How can I help you": "有什么可以帮您？",
    "How can I help you today": "今天有什么可以帮您？",
    "How can I help you today?": "今天有什么可以帮您？",
    "Type / for skills": "输入 / 唤起技能",
    "Send": "发送",
    "Send message": "发送消息",
    "Attach": "附加",
    "Attach files": "附加文件",
    "Add": "添加",
    "Take a photo": "拍照",
    "Use a photo": "使用照片",
    "Add photos and files": "添加照片和文件",
    "Create": "创建",
    "Plan": "计划",
    "Analyze": "分析",
    "Choose a style": "选择风格",
    "Thinking": "思考",
    "Extended thinking": "扩展思考",
    "Web search": "联网搜索",
    "Search the web": "联网搜索",
    "Connect": "连接",
    "Project": "项目",
    "Talk to Claude": "与 Claude 对话",
    "Speak": "说话",
    "Microphone": "麦克风",
    "Camera": "摄像头",
    "Stop voice": "停止语音",
    "Use microphone": "使用麦克风",
    "Summarize": "总结",
    "Explain": "解释",
    "Continue": "继续",
    "Type a message": "输入消息",
    "Press Enter to send": "按 Enter 发送",
    "Add a file": "添加文件",
    "Add photos": "添加照片",
    // ---- 消息 / 操作 ----
    "You": "你",
    "Copy": "复制",
    "Copied": "已复制",
    "Retry": "重试",
    "Edit": "编辑",
    "Delete": "删除",
    "Pin": "固定",
    "Unpin": "取消固定",
    "Share": "分享",
    "Save": "保存",
    "Saved": "已保存",
    "Regenerate": "重新生成",
    "Stop": "停止",
    "Stop generating": "停止生成",
    "Good response": "好回答",
    "Bad response": "差回答",
    "Thanks": "感谢",
    "Thinking…": "思考中…",
    "Claude is thinking": "Claude 正在思考",
    "Claude is typing": "Claude 正在输入",
    "Generating": "生成中",
    "Loading": "加载中",
    "Retry conversation": "重试对话",
    "View code": "查看代码",
    "Run": "运行",
    "Result": "结果",
    "Expand": "展开",
    "Collapse": "收起",
    "More": "更多",
    "Less": "更少",
    "Show more": "显示更多",
    "Show less": "显示更少",
    "See more": "查看更多",
    "Close": "关闭",
    "Cancel": "取消",
    "Confirm": "确认",
    "Submit": "提交",
    "OK": "确定",
    "Done": "完成",
    "Back": "返回",
    "Next": "下一步",
    "Previous": "上一步",
    "No": "否",
    "Yes": "是",
    "Accept": "接受",
    "Reject": "拒绝",
    "Open": "打开",
    "Open in": "在…中打开",
    // ---- 顶部菜单 ----
    "File": "文件",
    "Edit": "编辑",
    "View": "视图",
    "Window": "窗口",
    // ---- 通用 UI ----
    "Menu": "菜单",
    "Account": "账户",
    "Subscription": "订阅",
    "Plan": "套餐",
    "Free": "免费",
    "Pro": "专业版",
    "Max": "旗舰版",
    "Team": "团队版",
    "Enterprise": "企业版",
    "Trial": "试用",
    "Manage": "管理",
    "Manage subscription": "管理订阅",
    "Export": "导出",
    "Import": "导入",
    "Rename": "重命名",
    "Delete chat": "删除对话",
    "Delete project": "删除项目",
    "Archive chat": "归档对话",
    "Pin chat": "固定对话",
    "Share chat": "分享对话",
    "Copy link": "复制链接",
    "Copy text": "复制文本",
    "Select": "选择",
    "Select all": "全选",
    "Deselect": "取消选择",
    "Clear": "清除",
    "Clear conversation": "清除对话",
    "Start new chat": "开始新对话",
    "Ask anything": "问点什么",
    "Ask Claude": "问问 Claude",
    "Chat": "对话",
    "Conversation": "对话",
    "Composer": "输入框",
    "Prompt": "提示词",
    "Response": "回复",
    "Message": "消息",
    "Messages": "消息",
    "Notification": "通知",
    "Notifications": "通知",
    "Enable": "启用",
    "Disable": "禁用",
    "Turn on": "开启",
    "Turn off": "关闭",
    "On": "开",
    "Off": "关",
    "Auto": "自动",
    "Default": "默认",
    "None": "无",
    "All": "全部",
    "Today": "今天",
    "Yesterday": "昨天",
    "This week": "本周",
    "Last 7 days": "最近 7 天",
    "Last 30 days": "最近 30 天",
    "Search results": "搜索结果",
    "No results": "无结果",
    "No chats": "暂无对话",
    "No projects": "暂无项目",
    "Empty": "空",
    "Untitled": "未命名",
    "Beta": "测试版",
    // ---- 设置页（2026-09-18 截图补充）----
    "Preferences": "偏好设置",
    "Capabilities": "能力",
    "Memory": "记忆",
    "Reflect": "回顾",
    "Time and focus": "时间与专注",
    "Desktop app": "桌面应用",
    "Extensions": "扩展",
    "Developer": "开发者",
    "Skills": "技能",
    "Connectors": "连接器",
    "Plugins": "插件",
    "Chat font": "聊天字体",
    "Motion": "动效",
    "Reduce animation in streaming responses and other interface elements.": "减少流式回复与其他界面元素的动画效果。",
    "System": "跟随系统",
    "Reduced": "减弱",
    "Voice": "语音",
    "Style": "风格",
    "Speed": "语速",
    "Normal": "正常",
    "Response completions": "回复完成提醒",
    "Get notified when Claude has finished a response. Useful for long-running tasks.": "Claude 完成回复时通知你，适合长时间任务。",
    "Light": "浅色",
    "Dark": "深色",
    "Notifications": "通知",
    "Font": "字体",
    // ---- 设置页 ----
    "General": "通用",
    "Security": "安全",
    "Privacy": "隐私",
    "Data": "数据",
    "Connected apps": "已连接应用",
    "Integrations": "集成",
    "API keys": "API 密钥",
    "Billing": "账单",
    "Usage": "用量",
    "Models": "模型",
    "Feature": "功能",
    "Features": "功能",
    "Experimental": "实验性",
    "Keyboard shortcuts": "键盘快捷键",
    "Keyboard Shortcuts": "键盘快捷键",
    "Reset": "重置",
    "Reset all": "全部重置",
    "Save changes": "保存更改",
    "Discard": "丢弃",
    "Discard changes": "丢弃更改",
    // ---- 项目 ----
    "Project knowledge": "项目知识",
    "Project files": "项目文件",
    "Project settings": "项目设置",
    "Add project": "添加项目",
    "New project": "新建项目",
    "Project name": "项目名称",
    "Project instructions": "项目指令",
    "Custom instructions": "自定义指令",
    "Instructions": "指令",
    // ---- 占位符 / 输入提示 ----
    "Ask anything…": "问点什么…",
    "Ask anything...": "问点什么…",
    "Search chats…": "搜索对话…",
    "Search chats...": "搜索对话…",
    "Search…": "搜索…",
    "Search...": "搜索…",
    "Name your project…": "为项目命名…",
    "Name your project...": "为项目命名…",
    "Name your chat…": "为对话命名…",
    "Name your chat...": "为对话命名…",
    "Type a message…": "输入消息…",
    "Type a message...": "输入消息…",
    "Message Claude…": "给 Claude 发消息…",
    "Message Claude...": "给 Claude 发消息…"
  };

  var ATTRS = ['placeholder', 'title', 'aria-label', 'alt'];

  function trText(node) {
    if (!node || node.nodeType !== 3) return;
    var s = node.nodeValue;
    if (!s) return;
    var t = s.trim();
    if (!t) return;
    var r = MAP[t];
    if (r === undefined) {
      // 动态问候语："Evening, lime" / "Morning, xxx" / "Afternoon, xxx"
      var g = t.match(/^(Morning|Afternoon|Evening),\s*(.+)$/);
      if (g) {
        var gm = { Morning: "早上好", Afternoon: "下午好", Evening: "晚上好" }[g[1]];
        r = gm + "，" + g[2];
      } else {
        return;
      }
    }
    // 保留首尾空白
    var lead = (s.match(/^\s*/) || [''])[0];
    var tail = (s.match(/\s*$/) || [''])[0];
    node.nodeValue = lead + r + tail;
  }

  function trAttrs(el) {
    if (!el || el.nodeType !== 1 || !el.getAttribute) return;
    for (var i = 0; i < ATTRS.length; i++) {
      var name = ATTRS[i];
      var v = el.getAttribute(name);
      if (v && MAP[v.trim()] !== undefined) {
        el.setAttribute(name, MAP[v.trim()]);
      }
    }
  }

  function walk(root) {
    if (!root) return;
    trAttrs(root);
    try {
      var els = root.querySelectorAll ? root.querySelectorAll('[placeholder],[title],[aria-label],[alt]') : [];
      for (var i = 0; i < els.length; i++) trAttrs(els[i]);
    } catch (e) {}
    try {
      var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
      var n;
      while ((n = w.nextNode())) trText(n);
    } catch (e) {}
  }

  function boot() {
    walk(document);
    try {
      new MutationObserver(function (ms) {
        for (var i = 0; i < ms.length; i++) {
          var m = ms[i];
          if (m.type === 'characterData') { trText(m.target); continue; }
          var a = m.addedNodes;
          if (!a) continue;
          for (var j = 0; j < a.length; j++) {
            if (a[j].nodeType === 1) walk(a[j]);
            else if (a[j].nodeType === 3) trText(a[j]);
          }
        }
      }).observe(document, { childList: true, subtree: true, characterData: true });
    } catch (e) {}
    // 周期性补扫（覆盖懒加载 / 异步渲染）
    var delays = [600, 1500, 3000, 5000, 8000, 12000, 18000];
    for (var k = 0; k < delays.length; k++) {
      (function (d) { setTimeout(function () { walk(document); }, d); })(delays[k]);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
