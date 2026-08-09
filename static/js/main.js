/* Hive — main.js (Native App Polish & Interactive Features) */

// ── CSRF Helper ──────────────────────────────────────────────
function getCookie(name) {
  let val = null;
  if (document.cookie) {
    document.cookie.split(';').forEach(c => {
      c = c.trim();
      if (c.startsWith(name + '=')) val = decodeURIComponent(c.slice(name.length + 1));
    });
  }
  return val;
}
const csrftoken = getCookie('csrftoken');

// ── Auto-dismiss flash messages ──────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-autohide]').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.4s ease, max-height 0.4s ease, margin 0.4s ease';
      el.style.opacity = '0';
      el.style.maxHeight = '0';
      el.style.overflow = 'hidden';
      el.style.margin = '0';
      setTimeout(() => el.remove(), 450);
    }, parseInt(el.dataset.autohide) || 4000);
  });

  document.querySelectorAll('[data-dismiss]').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.closest('[data-autohide], .alert');
      if (target) {
        target.style.transition = 'opacity 0.2s ease';
        target.style.opacity = '0';
        setTimeout(() => target.remove(), 250);
      }
    });
  });
});

// ── Mobile Menu Drawer Toggle ─────────────────────────────────
function toggleMobileMenu() {
  const sidebar = document.getElementById('mobile-menu-drawer');
  const overlay = document.getElementById('mobile-overlay');
  if (!sidebar) return;
  const open = sidebar.classList.toggle('menu-open');
  if (overlay) overlay.classList.toggle('hidden', !open);
  document.body.style.overflow = open ? 'hidden' : '';
}

document.addEventListener('DOMContentLoaded', () => {
  const overlay = document.getElementById('mobile-overlay');
  if (overlay) overlay.addEventListener('click', toggleMobileMenu);
});

// ── Avatar Menu Toggle ─────────────────────────────────────────
function toggleAvatarMenu() {
  const menu = document.getElementById('avatar-menu');
  if (menu) menu.classList.toggle('hidden');
}

// ── Notification Dropdown Toggle ──────────────────────────────
function toggleNotificationDropdown(event) {
  if (event) event.preventDefault();
  const dropdown = document.getElementById('notif-dropdown');
  if (!dropdown) return;
  
  const isHidden = dropdown.style.display === 'none' || !dropdown.style.display;
  if (isHidden) {
    dropdown.style.display = 'block';
  } else {
    dropdown.style.display = 'none';
  }
}

document.addEventListener('click', (e) => {
  const avatarMenu = document.getElementById('avatar-menu');
  const avatarBtn = document.getElementById('avatar-btn');
  if (avatarMenu && !avatarMenu.contains(e.target) && avatarBtn && !avatarBtn.contains(e.target)) {
    avatarMenu.classList.add('hidden');
  }

  const notifDropdown = document.getElementById('notif-dropdown');
  const notifBtn = document.getElementById('notif-bell-btn');
  if (notifDropdown && !notifDropdown.contains(e.target) && notifBtn && !notifBtn.contains(e.target)) {
    notifDropdown.style.display = 'none';
  }
});

// ── Comment Drawer Toggle ─────────────────────────────────────
function toggleComments(postId) {
  const drawer = document.getElementById(`comments-drawer-${postId}`);
  if (!drawer) return;
  drawer.classList.toggle('hidden');
}

// ── Like Toggle & Double-Tap Heart Animation ─────────────────
const pendingLikeRequests = new Set();

function toggleLike(postId) {
  // Prevent rapid double-clicks while a request is in flight for this post
  if (pendingLikeRequests.has(postId)) return;
  pendingLikeRequests.add(postId);

  const btn = document.getElementById(`like-btn-${postId}`);
  const countEl = document.getElementById(`likes-count-${postId}`);
  const labelEl = document.getElementById(`likes-label-${postId}`);
  const icon = btn ? btn.querySelector('svg') : null;

  // Store previous UI state for rollback if server request fails
  const wasLiked = btn ? btn.classList.contains('liked') : false;
  const prevCount = countEl ? parseInt(countEl.textContent, 10) || 0 : 0;

  // Calculate optimistic state (< 10ms perceived delay)
  const isLiked = !wasLiked;
  const newCount = Math.max(0, isLiked ? prevCount + 1 : prevCount - 1);

  // Apply Optimistic UI updates
  if (btn) {
    btn.classList.toggle('liked', isLiked);
  }
  if (icon) {
    icon.setAttribute('fill', isLiked ? 'currentColor' : 'none');
  }
  if (countEl) {
    countEl.textContent = newCount;
  }
  if (labelEl) {
    labelEl.textContent = newCount === 1 ? 'like' : 'likes';
  }

  fetch(`/posts/${postId}/like/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrftoken,
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    }
  })
  .then(r => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  })
  .then(data => {
    if (data && data.success) {
      // Reconcile UI with authoritative response from Django
      if (btn) {
        btn.classList.toggle('liked', data.liked);
      }
      if (icon) {
        icon.setAttribute('fill', data.liked ? 'currentColor' : 'none');
      }
      if (countEl && typeof data.likes_count === 'number') {
        countEl.textContent = data.likes_count;
        if (labelEl) {
          labelEl.textContent = data.likes_count === 1 ? 'like' : 'likes';
        }
      }
    } else {
      // Rollback on server error
      rollbackLikeUI(btn, icon, countEl, labelEl, wasLiked, prevCount);
    }
  })
  .catch(err => {
    console.error("Like toggle failed:", err);
    // Rollback on network failure
    rollbackLikeUI(btn, icon, countEl, labelEl, wasLiked, prevCount);
  })
  .finally(() => {
    pendingLikeRequests.delete(postId);
  });
}

function rollbackLikeUI(btn, icon, countEl, labelEl, wasLiked, prevCount) {
  if (btn) {
    btn.classList.toggle('liked', wasLiked);
  }
  if (icon) {
    icon.setAttribute('fill', wasLiked ? 'currentColor' : 'none');
  }
  if (countEl) {
    countEl.textContent = prevCount;
  }
  if (labelEl) {
    labelEl.textContent = prevCount === 1 ? 'like' : 'likes';
  }
}

// Handle double tap on post media to trigger like
function handleDoubleTapLike(postId, mediaContainer) {
  let lastTap = 0;
  mediaContainer.addEventListener('touchend', (e) => {
    const currentTime = new Date().getTime();
    const tapLength = currentTime - lastTap;
    if (tapLength < 300 && tapLength > 0) {
      triggerHeartPop(postId, mediaContainer);
      toggleLike(postId);
      e.preventDefault();
    }
    lastTap = currentTime;
  });

  mediaContainer.addEventListener('dblclick', () => {
    triggerHeartPop(postId, mediaContainer);
    toggleLike(postId);
  });
}

function triggerHeartPop(postId, container) {
  const heart = container.querySelector('.double-tap-heart');
  if (heart) {
    heart.classList.remove('animate');
    void heart.offsetWidth; // Force reflow
    heart.classList.add('animate');
  }
}

// ── Save Toggle ───────────────────────────────────────────────
function toggleSave(postId) {
  fetch(`/posts/${postId}/save/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json' }
  })
  .then(r => r.json())
  .then(data => {
    if (!data.success) return;
    const btn = document.getElementById(`save-btn-${postId}`);
    if (btn) btn.classList.toggle('saved', data.saved);
  })
  .catch(() => {});
}

// ── Post Comment AJAX ─────────────────────────────────────────
function postComment(event, postId) {
  event.preventDefault();
  const form = event.target;
  const input = form.querySelector('input[name="content"]');
  if (!input || !input.value.trim()) return;
  const content = input.value;
  const formData = new FormData();
  formData.append('content', content);

  fetch(`/posts/${postId}/comment/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrftoken },
    body: formData
  })
  .then(r => r.json())
  .then(data => {
    if (!data.success) return;
    input.value = '';
    const list = document.getElementById(`comments-list-${postId}`);
    const noMsg = document.getElementById(`no-comments-msg-${postId}`);
    if (noMsg) noMsg.remove();

    const c = data.comment;
    const initials = c.author_name.split(' ').map(n => n[0]).join('');
    const avatarHTML = c.author_avatar
      ? `<img src="${c.author_avatar}" alt="" class="w-full h-full object-cover">`
      : `<span>${initials}</span>`;

    const html = `
      <div class="comment-bubble flex items-start gap-2.5 animate-fade-up" id="comment-${c.id}">
        <a href="/profile/${c.author_username}/" class="avatar avatar-sm flex-shrink-0">${avatarHTML}</a>
        <div class="flex-1 min-w-0">
          <div class="flex items-baseline justify-between gap-2 mb-0.5">
            <a href="/profile/${c.author_username}/" class="text-xs font-bold text-gray-900 hover:text-emerald-600">${c.author_name}</a>
            <span class="text-[10px] text-gray-400">${c.created_at}</span>
          </div>
          <p class="text-xs text-gray-700">${c.content}</p>
        </div>
      </div>`;
    list.insertAdjacentHTML('beforeend', html);

    const counter = document.getElementById(`comments-count-${postId}`);
    if (counter) counter.textContent = list.children.length;

    const drawer = document.getElementById(`comments-drawer-${postId}`);
    if (drawer && !drawer.classList.contains('hidden')) {
      drawer.classList.add('hidden');
    }
  })
  .catch(() => {});
}

// ── Fullscreen Media Viewer (Lightbox) ───────────────────────
function openLightbox(imageSrc) {
  const modal = document.getElementById('lightbox-modal');
  const img = document.getElementById('lightbox-img');
  if (!modal || !img) return;
  img.src = imageSrc;
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  const modal = document.getElementById('lightbox-modal');
  if (!modal) return;
  modal.classList.remove('active');
  document.body.style.overflow = '';
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeLightbox();
});

// ── Infinite Scroll Handler ──────────────────────────────────
let currentPage = 1;
let isLoadingFeed = false;
let hasMorePosts = true;
let isObserverInitialized = false;
const loadedPostIds = new Set();

function initInfiniteScroll() {
  const trigger = document.getElementById('infinite-scroll-trigger');
  const container = document.getElementById('feed-container');
  if (!trigger || !container) return;

  if (isObserverInitialized) return;
  isObserverInitialized = true;

  // Track existing DOM post IDs on initial page load
  container.querySelectorAll('.post-card').forEach(post => {
    const rawId = post.id || '';
    const numId = rawId.replace('post-', '');
    if (numId) loadedPostIds.add(numId);
  });

  const observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !isLoadingFeed && hasMorePosts) {
      loadNextPage();
    }
  }, { rootMargin: '300px' });

  observer.observe(trigger);
}

function loadNextPage() {
  if (isLoadingFeed || !hasMorePosts) return;
  isLoadingFeed = true;
  
  const container = document.getElementById('feed-container');
  const skeleton = document.getElementById('feed-skeleton-loader');
  if (skeleton) skeleton.classList.remove('hidden');

  fetch(`?page=${currentPage + 1}`, {
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
  .then(r => {
    if (r.status === 444 || r.status === 404 || !r.ok) {
      hasMorePosts = false;
      return null;
    }
    return r.text();
  })
  .then(html => {
    if (skeleton) skeleton.classList.add('hidden');
    isLoadingFeed = false;
    if (html && html.trim().length > 50) {
      currentPage++;
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const newPosts = doc.querySelectorAll('.post-card');
      if (newPosts.length === 0) {
        hasMorePosts = false;
        return;
      }
      
      let addedCount = 0;
      newPosts.forEach(post => {
        const rawId = post.id || '';
        const numId = rawId.replace('post-', '');
        if (!numId || !loadedPostIds.has(numId)) {
          if (numId) loadedPostIds.add(numId);
          container.appendChild(post.cloneNode(true));
          addedCount++;
        }
      });

      if (addedCount === 0) {
        hasMorePosts = false;
      }
    } else {
      hasMorePosts = false;
    }
  })
  .catch(() => {
    if (skeleton) skeleton.classList.add('hidden');
    isLoadingFeed = false;
    hasMorePosts = false;
  });
}

// ── Follow / Unfollow AJAX Handler ───────────────────────────
function initFollowToggleHandlers() {
  document.addEventListener('submit', (e) => {
    const form = e.target;
    if (form && form.action && form.action.includes('/follow/')) {
      e.preventDefault();
      
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        if (submitBtn.disabled) return;
        submitBtn.disabled = true;
        submitBtn.dataset.originalText = submitBtn.textContent;
        submitBtn.textContent = '...';
      }

      // Extract target user_id from form action URL or dataset
      let userId = form.dataset.followUserId;
      if (!userId && form.action) {
        const parts = form.action.split('/follow/')[0].split('/');
        userId = parts[parts.length - 1];
      }

      fetch(form.action, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrftoken,
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          // Find all buttons matching target userId if available, else fallback to submitBtn
          const targetButtons = userId ? document.querySelectorAll(`button[data-follow-btn-user-id="${userId}"]`) : [];
          const buttonsToUpdate = targetButtons.length > 0 ? Array.from(targetButtons) : (submitBtn ? [submitBtn] : []);

          buttonsToUpdate.forEach(btn => {
            const isNotifBtn = btn.classList.contains('notif-row-btn-primary') || btn.classList.contains('notif-row-btn-secondary');
            if (data.following) {
              btn.textContent = 'Following';
              if (isNotifBtn) {
                btn.className = 'notif-row-btn-secondary';
              } else {
                btn.className = btn.className.replace('net-btn-follow', 'net-btn-following').replace('btn-primary', 'btn-secondary');
              }
            } else {
              btn.textContent = isNotifBtn ? 'Follow Back' : 'Follow';
              if (isNotifBtn) {
                btn.className = 'notif-row-btn-primary';
              } else {
                btn.className = btn.className.replace('net-btn-following', 'net-btn-follow').replace('btn-secondary', 'btn-primary');
              }
            }
            btn.disabled = false;
          });

          // Also update network/followers card counts if present
          if (userId) {
            const followerCountEl = document.getElementById(`follower-count-${userId}`);
            if (followerCountEl && data.follower_count !== undefined) {
              followerCountEl.textContent = data.follower_count;
            }
          }
        } else if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = submitBtn.dataset.originalText || 'Follow Back';
        }
      })
      .catch(() => {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = submitBtn.dataset.originalText || 'Follow Back';
        }
      });
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initInfiniteScroll();
  initFeedVideoAutoplay();
  initNavbarUserSearch();
  initFollowToggleHandlers();
});

// ── Toast Notification System ──────────────────────────────
function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full px-4 pointer-events-none';
    document.body.appendChild(container);
  }

  const bgClasses = type === 'success' ? 'bg-emerald-600 text-white' : type === 'error' ? 'bg-rose-600 text-white' : 'bg-slate-800 text-white';
  const toast = document.createElement('div');
  toast.className = `p-3.5 rounded-xl shadow-xl text-xs font-semibold flex items-center justify-between pointer-events-auto animate-fade-up ${bgClasses}`;
  toast.innerHTML = `<span>${message}</span><button onclick="this.parentElement.remove()" class="ml-3 font-bold opacity-75 hover:opacity-100">&times;</button>`;
  
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}



// ── Feed Video IntersectionObserver Autoplay (Single Active Video) ─────────────
let currentlyPlayingVideo = null;

function initFeedVideoAutoplay() {
  const videos = document.querySelectorAll('video.feed-video-player');
  if (!videos.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      const video = entry.target;
      if (entry.isIntersecting) {
        if (currentlyPlayingVideo && currentlyPlayingVideo !== video) {
          currentlyPlayingVideo.pause();
        }
        video.muted = true;
        video.play().then(() => {
          currentlyPlayingVideo = video;
        }).catch(() => {});
      } else {
        if (currentlyPlayingVideo === video) {
          video.pause();
          currentlyPlayingVideo = null;
        }
      }
    });
  }, { threshold: 0.5 });

  videos.forEach(v => observer.observe(v));
}

// ── Global Standardized Delete Modal & Handler System ────────────────────────────
let globalDeleteState = {
  url: null,
  targetElement: null,
  redirectUrl: null,
  objectType: 'item',
  formElement: null
};

function openGlobalDeleteModal(options) {
  // options: { url, objectType, objectTitle, targetElementId, redirectUrl, formId }
  const modal = document.getElementById('global-delete-modal');
  if (!modal) return;

  const titleEl = document.getElementById('delete-modal-title');
  const messageEl = document.getElementById('delete-modal-message');
  const confirmBtn = document.getElementById('delete-modal-confirm-btn');
  const confirmText = document.getElementById('delete-modal-confirm-text');

  const itemType = options.objectType || 'item';
  const itemTitle = options.objectTitle ? ` "${options.objectTitle}"` : '';

  if (titleEl) titleEl.textContent = `Delete ${itemType.charAt(0).toUpperCase() + itemType.slice(1)}?`;
  if (messageEl) messageEl.textContent = `Are you sure you want to permanently delete this ${itemType}${itemTitle}? This action cannot be undone.`;
  if (confirmText) confirmText.textContent = 'Delete';

  globalDeleteState = {
    url: options.url || (options.formId ? document.getElementById(options.formId)?.action : null),
    targetElement: options.targetElementId ? document.getElementById(options.targetElementId) : null,
    redirectUrl: options.redirectUrl || null,
    objectType: itemType,
    formElement: options.formId ? document.getElementById(options.formId) : null
  };

  confirmBtn.onclick = handleGlobalDeleteConfirm;
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeGlobalDeleteModal() {
  const modal = document.getElementById('global-delete-modal');
  if (modal) modal.classList.add('hidden');
  document.body.style.overflow = '';
}

// Close delete modal on Escape key or outside click
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeGlobalDeleteModal();
});

document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('global-delete-modal');
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeGlobalDeleteModal();
    });
  }
});

function handleGlobalDeleteConfirm() {
  const confirmBtn = document.getElementById('delete-modal-confirm-btn');
  const confirmText = document.getElementById('delete-modal-confirm-text');
  if (!globalDeleteState.url && !globalDeleteState.formElement) return;

  if (confirmBtn) confirmBtn.disabled = true;
  if (confirmText) confirmText.textContent = 'Deleting…';

  // If formElement exists and no AJAX target element / redirect specified, submit form natively
  if (globalDeleteState.formElement && !globalDeleteState.targetElement && !globalDeleteState.redirectUrl) {
    globalDeleteState.formElement.submit();
    return;
  }

  const actionUrl = globalDeleteState.url || globalDeleteState.formElement.action;

  fetch(actionUrl, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrftoken,
      'X-Requested-With': 'XMLHttpRequest'
    }
  })
  .then(r => {
    if (r.redirected) {
      window.location.href = r.url;
      return null;
    }
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  })
  .then(data => {
    if (data === null) return; // Handled by redirect
    closeGlobalDeleteModal();
    if (confirmBtn) confirmBtn.disabled = false;

    if (data && data.success) {
      if (globalDeleteState.targetElement) {
        globalDeleteState.targetElement.style.transition = 'opacity 0.3s ease, transform 0.3s ease, max-height 0.3s ease, margin 0.3s ease';
        globalDeleteState.targetElement.style.opacity = '0';
        globalDeleteState.targetElement.style.transform = 'scale(0.95)';
        setTimeout(() => globalDeleteState.targetElement.remove(), 300);
      }
      showToast(`${globalDeleteState.objectType.charAt(0).toUpperCase() + globalDeleteState.objectType.slice(1)} deleted successfully.`, 'success');

      if (globalDeleteState.redirectUrl) {
        setTimeout(() => { window.location.href = globalDeleteState.redirectUrl; }, 400);
      }
    } else {
      showToast(`Unable to delete ${globalDeleteState.objectType}. Please try again.`, 'error');
    }
  })
  .catch(err => {
    console.error("Delete failed:", err);
    closeGlobalDeleteModal();
    if (confirmBtn) confirmBtn.disabled = false;
    // Fallback: If non-JSON response (e.g. standard Django HTTP redirect response), perform navigation if redirectUrl set
    if (globalDeleteState.redirectUrl) {
      window.location.href = globalDeleteState.redirectUrl;
    } else if (globalDeleteState.formElement) {
      globalDeleteState.formElement.submit();
    } else {
      showToast(`Unable to delete ${globalDeleteState.objectType}. Please try again.`, 'error');
    }
  });
}

// Deprecated alias for backwards compatibility
function confirmDeletePost(actionUrl, targetPostId) {
  openGlobalDeleteModal({
    url: actionUrl,
    objectType: 'post',
    targetElementId: targetPostId ? `post-${targetPostId}` : null
  });
}

