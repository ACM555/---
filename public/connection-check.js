(function () {
  const results = document.getElementById('results');
  const summary = document.getElementById('summary');
  const retry = document.getElementById('retry');
  const baseUrl = new URL('.', window.location.href);
  let reportLines = [];
  let failures = 0;
  let frame = null;

  function record(name, success, detail) {
    if (!success) failures += 1;
    reportLines.push((success ? '通过' : '失败') + '｜' + name + '｜' + detail);
    results.textContent = reportLines.join('\n');
  }

  async function download(url) {
    const startedAt = Date.now();
    const controller = new AbortController();
    const timeout = setTimeout(function () { controller.abort(); }, 20000);
    try {
      const response = await fetch(url, { cache: 'no-store', credentials: 'omit', signal: controller.signal });
      const text = await response.text();
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return {
        text: text,
        contentType: response.headers.get('content-type') || '',
        elapsed: Date.now() - startedAt,
        url: response.url,
      };
    } finally {
      clearTimeout(timeout);
    }
  }

  async function checkResource(name, url, expectedType) {
    try {
      const resource = await download(url);
      if (!expectedType.test(resource.contentType)) throw new Error('响应类型不正确：' + resource.contentType);
      if (/^\s*<!doctype|^\s*<html/i.test(resource.text)) throw new Error('资源被返回成 HTML 网页');
      record(name, true, resource.text.length + ' 字符；' + resource.elapsed + 'ms；' + resource.contentType);
    } catch (error) {
      record(name, false, error.message + '；' + url.pathname);
    }
  }

  async function checkPageStartup() {
    frame = document.createElement('iframe');
    frame.title = '东盟体验启动检测';
    frame.src = new URL('?diagnostic=' + Date.now() + '#/experience', baseUrl).href;
    document.body.appendChild(frame);
    const startedAt = Date.now();
    while (Date.now() - startedAt < 25000) {
      await new Promise(function (resolve) { setTimeout(resolve, 250); });
      try {
        const frameDocument = frame.contentDocument;
        if (!frameDocument) continue;
        const errors = frame.contentWindow.aseanBootDiagnostics;
        if (errors && errors.errors.length) {
          record('页面实际启动', false, errors.errors.join('；'));
          return;
        }
        if (frameDocument.querySelector('.experience-card')) {
          record('页面实际启动', true, '体验页已渲染；' + (Date.now() - startedAt) + 'ms');
          return;
        }
        const errorHeading = frameDocument.querySelector('.boot-fallback h1');
        if (errorHeading && errorHeading.textContent === '页面加载失败') {
          record('页面实际启动', false, '页面进入错误保护状态');
          return;
        }
      } catch (error) {
        record('页面实际启动', false, error.message);
        return;
      }
    }
    record('页面实际启动', false, '25 秒仍未渲染体验页，请同时提供体验页截图');
  }

  async function run() {
    if (frame) frame.remove();
    reportLines = ['检测时间：' + new Date().toISOString(), '入口：' + baseUrl.href, '浏览器：' + navigator.userAgent];
    failures = 0;
    retry.disabled = true;
    summary.textContent = '正在检测，请等待约 30 秒……';
    results.textContent = reportLines.join('\n');
    try {
      record('模块支持', 'noModule' in document.createElement('script'), 'JavaScript 模块');
      const storageKey = '__asean_connection_probe_' + Date.now();
      try {
        localStorage.setItem(storageKey, 'ok');
        const readable = localStorage.getItem(storageKey) === 'ok';
        localStorage.removeItem(storageKey);
        record('浏览器存储', readable, '登录状态所需的本地存储');
      } catch (error) {
        record('浏览器存储', false, error.message);
      }
      try {
        const health = await download(new URL('api/health', baseUrl));
        const payload = JSON.parse(health.text);
        record('后端接口', payload.status === 'ok', 'HTTP 200；' + health.elapsed + 'ms');
      } catch (error) {
        record('后端接口', false, error.message);
      }
      const entry = await download(new URL('?diagnostic=' + Date.now(), baseUrl));
      const entryDocument = new DOMParser().parseFromString(entry.text, 'text/html');
      const scripts = entryDocument.querySelectorAll('script[type="module"][src]');
      const script = scripts[scripts.length - 1];
      const stylesheet = entryDocument.querySelector('link[rel="stylesheet"][href]');
      record('入口网页', Boolean(script), 'HTTP 200；' + entry.elapsed + 'ms');
      if (!script) throw new Error('入口没有找到应用模块脚本');
      const checks = [checkResource('主脚本下载', new URL(script.getAttribute('src'), entry.url), /javascript|ecmascript/i)];
      if (stylesheet) checks.push(checkResource('样式下载', new URL(stylesheet.getAttribute('href'), entry.url), /text\/css/i));
      await Promise.all(checks);
      await checkPageStartup();
    } catch (error) {
      record('诊断执行', false, error.message);
    } finally {
      if (frame) frame.remove();
      retry.disabled = false;
      summary.textContent = failures
        ? '检测完成，有 ' + failures + ' 项失败。请将检查结果连同地址栏截图发给维护人员。'
        : '检测全部通过，当前链路能够启动东盟体验页。如果仍打不开，请提供原体验页地址栏和页面截图。';
    }
  }

  retry.addEventListener('click', run);
  run();
})();
