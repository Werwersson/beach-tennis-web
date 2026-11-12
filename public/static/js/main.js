// ============================================================
// BEACH TENNIS WEB — Scripts Globais
// ============================================================

document.addEventListener('DOMContentLoaded', function () {

  // ---- Sidebar toggle (mobile) ----
  var btnToggle = document.getElementById('btnToggleSidebar');
  var sidebar   = document.getElementById('adminSidebar');
  var overlay   = document.getElementById('sidebarOverlay');

  function openSidebar() {
    sidebar && sidebar.classList.add('show');
    overlay && overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
  function closeSidebar() {
    sidebar && sidebar.classList.remove('show');
    overlay && overlay.classList.remove('show');
    document.body.style.overflow = '';
  }
  btnToggle && btnToggle.addEventListener('click', openSidebar);
  overlay   && overlay.addEventListener('click', closeSidebar);

  // ---- Auto-dismiss de alertas após 5s ----
  document.querySelectorAll('.alert-dismissible.auto-dismiss').forEach(function (el) {
    setTimeout(function () {
      var bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert && bsAlert.close();
    }, 5000);
  });

  // ---- Preview de foto antes do upload ----
  var inputFoto = document.getElementById('foto');
  var previewFoto = document.getElementById('fotoPreview');
  var fotoAvatar = document.getElementById('fotoAvatar');
  if (inputFoto && previewFoto) {
    inputFoto.addEventListener('change', function () {
      var file = this.files[0];
      if (file) {
        var reader = new FileReader();
        reader.onload = function (e) {
          previewFoto.src = e.target.result;
          previewFoto.classList.remove('d-none');
          if (fotoAvatar) fotoAvatar.classList.add('d-none');
        };
        reader.readAsDataURL(file);
      }
    });
  }

  // ---- Tooltip Bootstrap ----
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
    new bootstrap.Tooltip(el, { trigger: 'hover' });
  });

  // ---- Confirm delete ----
  document.querySelectorAll('.btn-confirm-delete').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      var msg = this.dataset.msg || 'Tem certeza que deseja excluir? Esta ação não pode ser desfeita.';
      if (!confirm(msg)) e.preventDefault();
    });
  });

  // ---- Marcar nav-link ativo na sidebar ----
  var currentPath = window.location.pathname;
  document.querySelectorAll('.sidebar-nav .nav-link').forEach(function (link) {
    var href = link.getAttribute('href');
    if (href && currentPath.startsWith(href) && href !== '/') {
      link.classList.add('active');
    }
  });

  // ---- Sortable para plano de aula (Drag & Drop) ----
  var sortableList = document.getElementById('exerciciosSortable');
  if (sortableList && typeof Sortable !== 'undefined') {
    Sortable.create(sortableList, {
      animation: 150,
      handle: '.drag-handle',
      ghostClass: 'sortable-ghost',
      onEnd: function () { atualizarOrdens(); }
    });
  }
  function atualizarOrdens() {
    document.querySelectorAll('#exerciciosSortable .exercicio-item').forEach(function (el, idx) {
      var inputOrdem = el.querySelector('.input-ordem');
      if (inputOrdem) inputOrdem.value = idx + 1;
    });
  }

  // ---- Máscara de telefone ----
  document.querySelectorAll('.mask-phone').forEach(function (el) {
    el.addEventListener('input', function () {
      var v = this.value.replace(/\D/g, '').substring(0, 11);
      if (v.length <= 10) {
        v = v.replace(/(\d{2})(\d{4})(\d{0,4})/, '($1) $2-$3');
      } else {
        v = v.replace(/(\d{2})(\d{5})(\d{0,4})/, '($1) $2-$3');
      }
      this.value = v;
    });
  });

  // ---- Scroll âncoras da página pública ----
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      var target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        var offset = 70;
        window.scrollTo({ top: target.offsetTop - offset, behavior: 'smooth' });
      }
    });
  });

  // ---- WhatsApp link com mensagem ----
  document.querySelectorAll('.btn-whatsapp').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var tel = this.dataset.tel || '';
      var msg = this.dataset.msg || 'Olá! Gostaria de saber mais sobre as aulas de Beach Tennis.';
      var url = 'https://wa.me/' + tel.replace(/\D/g, '') + '?text=' + encodeURIComponent(msg);
      window.open(url, '_blank');
    });
  });

});

// ---- Utilitários globais ----
window.BT = {
  toast: function (msg, tipo) {
    tipo = tipo || 'success';
    var container = document.getElementById('toastContainer');
    if (!container) return;
    var id = 'toast-' + Date.now();
    var icons = { success: 'check-circle-fill', danger: 'x-circle-fill', warning: 'exclamation-triangle-fill', info: 'info-circle-fill' };
    var icon = icons[tipo] || 'info-circle-fill';
    container.insertAdjacentHTML('beforeend',
      '<div id="' + id + '" class="toast align-items-center text-bg-' + tipo + ' border-0 show" role="alert">' +
        '<div class="d-flex">' +
          '<div class="toast-body d-flex align-items-center gap-2">' +
            '<i class="bi bi-' + icon + '"></i>' + msg +
          '</div>' +
          '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>' +
        '</div>' +
      '</div>'
    );
    setTimeout(function () {
      var el = document.getElementById(id);
      if (el) {
        var t = bootstrap.Toast.getOrCreateInstance(el);
        t.hide();
        setTimeout(function () { el.remove(); }, 500);
      }
    }, 4000);
  },

  formatDate: function (isoStr) {
    if (!isoStr) return '-';
    var d = new Date(isoStr);
    return d.toLocaleDateString('pt-BR');
  }
};
