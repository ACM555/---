(function () {
  var diagnostics = { errors: [] };
  window.aseanBootDiagnostics = diagnostics;

  function report(message) {
    if (diagnostics.errors.length < 10) diagnostics.errors.push(message);
    var status = document.getElementById('boot-status');
    if (status) status.textContent = message + '。请打开下方连接诊断。';
  }

  window.addEventListener('error', function (event) {
    var target = event.target;
    if (target && (target.tagName === 'SCRIPT' || target.tagName === 'LINK')) {
      var source = target.src || target.href || '';
      report('资源加载失败：' + source.split('?')[0].split('/').pop());
    } else if (event.message) {
      report('前端运行异常：' + event.message);
    }
  }, true);

  window.addEventListener('unhandledrejection', function (event) {
    var reason = event.reason;
    report('前端运行异常：' + (reason && reason.message ? reason.message : String(reason)));
  });

  window.setTimeout(function () {
    var status = document.getElementById('boot-status');
    if (status && !diagnostics.errors.length) {
      status.textContent = '页面脚本超过 15 秒仍未完成启动。请打开下方连接诊断。';
    }
  }, 15000);
})();
