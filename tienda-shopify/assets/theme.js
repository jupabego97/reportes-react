/**
 * NANO Tech Store - JavaScript 2026
 * Theme Toggle, Staggered Reveals, Low-Carbon optimizado
 */

(function() {
  'use strict';

  // ============================================
  // THEME TOGGLE - Dark/Light Mode
  // ============================================
  const ThemeManager = {
    STORAGE_KEY: 'nano-theme',
    
    init() {
      this.toggle = document.getElementById('theme-toggle');
      this.setInitialTheme();
      this.bindEvents();
    },
    
    setInitialTheme() {
      // Check localStorage first
      const savedTheme = localStorage.getItem(this.STORAGE_KEY);
      
      if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
      } else {
        // Check system preference
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
      }
    },
    
    bindEvents() {
      if (this.toggle) {
        this.toggle.addEventListener('click', () => this.toggleTheme());
      }
      
      // Listen for system preference changes
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem(this.STORAGE_KEY)) {
          document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
        }
      });
    },
    
    toggleTheme() {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem(this.STORAGE_KEY, newTheme);
      
      // Announce to screen readers
      this.announceThemeChange(newTheme);
    },
    
    announceThemeChange(theme) {
      const announcement = document.createElement('div');
      announcement.setAttribute('role', 'status');
      announcement.setAttribute('aria-live', 'polite');
      announcement.className = 'visually-hidden';
      announcement.textContent = `Tema cambiado a ${theme === 'dark' ? 'oscuro' : 'claro'}`;
      document.body.appendChild(announcement);
      
      setTimeout(() => announcement.remove(), 1000);
    }
  };

  // ============================================
  // REVEAL ANIMATIONS - Staggered on scroll
  // ============================================
  const RevealManager = {
    init() {
      if (!('IntersectionObserver' in window)) {
        // Fallback: show all elements
        document.querySelectorAll('.reveal, .reveal-stagger').forEach(el => {
          el.classList.add('revealed');
        });
        return;
      }
      
      this.setupObserver();
    },
    
    setupObserver() {
      const options = {
        root: null,
        rootMargin: '0px 0px -50px 0px',
        threshold: 0.1
      };
      
      this.observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            this.observer.unobserve(entry.target);
          }
        });
      }, options);
      
      // Observe all reveal elements
      document.querySelectorAll('.reveal, .reveal-stagger').forEach(el => {
        this.observer.observe(el);
      });
    }
  };

  // ============================================
  // CART MANAGER - AJAX Cart functionality
  // ============================================
  const CartManager = {
    init() {
      this.updateCartCount();
      this.bindFormSubmissions();
    },
    
    async updateCartCount() {
      try {
        const response = await fetch('/cart.js');
        const cart = await response.json();
        
        document.querySelectorAll('.cart-count, [data-cart-count], .header__cart-count').forEach(counter => {
          counter.textContent = cart.item_count;
          counter.classList.toggle('hidden', cart.item_count === 0);
        });
        
        return cart;
      } catch (error) {
        console.error('Error updating cart:', error);
      }
    },
    
    bindFormSubmissions() {
      document.addEventListener('submit', async (e) => {
        const form = e.target;
        
        // Solo manejar formularios de carrito que NO tengan data-product-form
        // Los formularios con data-product-form tienen su propio handler en main-product.liquid
        if (form.matches('[action="/cart/add"]') && !form.hasAttribute('data-product-form')) {
          // Skip if checkout button was clicked
          if (e.submitter && e.submitter.name === 'checkout') return;
          
          e.preventDefault();
          await this.handleAddToCart(form);
        }
      });
    },
    
    async handleAddToCart(form) {
      const submitBtn = form.querySelector('[type="submit"]');
      const originalContent = submitBtn ? submitBtn.innerHTML : '';
      
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
          </svg>
          <span>Agregando...</span>
        `;
      }
      
      try {
        // Obtener datos del formulario
        const variantId = form.querySelector('[name="id"]')?.value;
        const quantity = parseInt(form.querySelector('[name="quantity"]')?.value) || 1;
        
        console.log('Quick add to cart:', { variantId, quantity });
        
        if (!variantId) {
          throw new Error('No se pudo identificar el producto');
        }

        const response = await fetch('/cart/add.js', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({
            items: [{
              id: parseInt(variantId),
              quantity: quantity
            }]
          })
        });
        
        const result = await response.json();
        console.log('Cart add response:', result);
        
        if (response.ok) {
          await this.updateCartCount();
          
          if (submitBtn) {
            submitBtn.innerHTML = `
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
              <span>¡Agregado!</span>
            `;
            submitBtn.style.background = 'var(--color-success)';
          }
          
          const itemTitle = result.items ? result.items[0].product_title : (result.product_title || result.title || 'Producto');
          NotificationManager.show(`"${itemTitle}" agregado al carrito`, 'success');
          
          setTimeout(() => {
            if (submitBtn) {
              submitBtn.disabled = false;
              submitBtn.innerHTML = originalContent;
              submitBtn.style.background = '';
            }
          }, 2000);
        } else {
          console.error('Cart error response:', result);
          throw new Error(result.description || result.message || 'Error al agregar');
        }
      } catch (error) {
        console.error('Cart error:', error);
        NotificationManager.show(error.message || 'Error al agregar el producto', 'error');
        
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalContent;
        }
      }
    }
  };

  // ============================================
  // NOTIFICATION MANAGER - Toast notifications
  // ============================================
  const NotificationManager = {
    show(message, type = 'info') {
      // Remove existing notification
      const existing = document.querySelector('.notification-toast');
      if (existing) existing.remove();
      
      const notification = document.createElement('div');
      notification.className = 'notification-toast';
      notification.setAttribute('role', 'alert');
      notification.setAttribute('aria-live', 'polite');
      
      const icons = {
        success: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        error: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        info: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
      };
      
      const colors = {
        success: 'var(--color-success)',
        error: 'var(--color-error)',
        info: 'var(--color-accent)'
      };
      
      notification.innerHTML = `
        <div class="notification-toast__icon">${icons[type]}</div>
        <div class="notification-toast__message">${message}</div>
        <button class="notification-toast__close" aria-label="Cerrar">&times;</button>
      `;
      
      notification.style.cssText = `
        position: fixed;
        bottom: 24px;
        left: 50%;
        transform: translateX(-50%) translateY(100px);
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px 20px;
        background: ${colors[type]};
        color: white;
        font-family: var(--font-body);
        font-size: 14px;
        font-weight: 500;
        border-radius: var(--radius-xl);
        box-shadow: var(--shadow-xl);
        z-index: var(--z-toast);
        transition: transform 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        max-width: calc(100vw - 48px);
      `;
      
      document.body.appendChild(notification);
      
      // Close button
      notification.querySelector('.notification-toast__close').addEventListener('click', () => {
        this.hide(notification);
      });
      
      // Animate in
      requestAnimationFrame(() => {
        notification.style.transform = 'translateX(-50%) translateY(0)';
      });
      
      // Auto close
      setTimeout(() => this.hide(notification), 4000);
    },
    
    hide(notification) {
      if (!notification.parentNode) return;
      notification.style.transform = 'translateX(-50%) translateY(100px)';
      setTimeout(() => notification.remove(), 400);
    }
  };

  // Make notification available globally
  window.showNotification = NotificationManager.show.bind(NotificationManager);

  // ============================================
  // QUANTITY SELECTOR (solo para páginas de producto, NO para carrito)
  // ============================================
  const QuantityManager = {
    init() {
      // Solo manejar selectores de cantidad en páginas de producto
      // El carrito tiene su propio sistema de manejo
      document.addEventListener('click', (e) => {
        const btn = e.target.closest('.quantity-btn, [data-action="minus"], [data-action="plus"]');
        if (!btn) return;
        
        // IMPORTANTE: NO manejar NADA relacionado con el carrito
        if (btn.closest('.cart-item')) return;
        if (btn.closest('.cart-section')) return;
        if (btn.closest('[data-cart-items]')) return;
        if (document.body.classList.contains('template-cart')) return;
        
        // NO manejar botones con data-action="decrease", "increase" o "remove"
        const action = btn.dataset.action;
        if (action === 'decrease' || action === 'increase' || action === 'remove') return;
        
        const container = btn.closest('.quantity-selector') || btn.parentElement;
        const input = container.querySelector('.quantity-input, input[type="number"]');
        if (!input) return;
        
        // Si el input está dentro del carrito, no hacer nada
        if (input.closest('.cart-item') || input.closest('.cart-section')) return;
        
        let value = parseInt(input.value) || 1;
        const btnAction = action || (btn.classList.contains('quantity-btn--minus') ? 'minus' : 'plus');
        
        if (btnAction === 'minus') {
          value = Math.max(1, value - 1);
        } else {
          value = value + 1;
        }
        
        input.value = value;
        // NO disparar evento change para evitar conflictos
      });
    }
  };

  // ============================================
  // SMOOTH SCROLL
  // ============================================
  const SmoothScroll = {
    init() {
      document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
          const href = anchor.getAttribute('href');
          if (href === '#') return;
          
          const target = document.querySelector(href);
          if (target) {
            e.preventDefault();
            target.scrollIntoView({
              behavior: 'smooth',
              block: 'start'
            });
          }
        });
      });
    }
  };

  // ============================================
  // LAZY LOADING IMAGES
  // ============================================
  const LazyLoader = {
    init() {
      if (!('IntersectionObserver' in window)) return;
      
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            if (img.dataset.src) {
              img.src = img.dataset.src;
              img.removeAttribute('data-src');
            }
            img.classList.add('loaded');
            observer.unobserve(img);
          }
        });
      }, {
        rootMargin: '50px 0px'
      });
      
      document.querySelectorAll('img[data-src], img[loading="lazy"]').forEach(img => {
        observer.observe(img);
      });
    }
  };

  // ============================================
  // ACCESSIBILITY ENHANCEMENTS
  // ============================================
  const A11y = {
    init() {
      // Skip to content
      const skipLink = document.querySelector('.skip-to-content-link');
      if (skipLink) {
        skipLink.addEventListener('click', (e) => {
          e.preventDefault();
          const target = document.querySelector(skipLink.getAttribute('href'));
          if (target) {
            target.setAttribute('tabindex', '-1');
            target.focus();
          }
        });
      }
      
      // Keyboard navigation for dropdowns
      document.querySelectorAll('.header__menu-item--dropdown').forEach(item => {
        const link = item.querySelector('.header__menu-link');
        const dropdown = item.querySelector('.header__dropdown');
        
        if (link && dropdown) {
          link.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              dropdown.style.opacity = '1';
              dropdown.style.visibility = 'visible';
              dropdown.style.transform = 'translateY(0)';
              dropdown.querySelector('a')?.focus();
            }
          });
          
          dropdown.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
              dropdown.style.opacity = '0';
              dropdown.style.visibility = 'hidden';
              dropdown.style.transform = 'translateY(10px)';
              link.focus();
            }
          });
        }
      });
    }
  };

  // ============================================
  // BUTTON FEEDBACK
  // ============================================
  const ButtonFeedback = {
    init() {
      const buttons = document.querySelectorAll('.btn, .hero-button, .product-card__btn');
      
      buttons.forEach(btn => {
        btn.addEventListener('mousedown', function() {
          this.style.transform = 'scale(0.97)';
        });
        
        ['mouseup', 'mouseleave'].forEach(event => {
          btn.addEventListener(event, function() {
            this.style.transform = '';
          });
        });
      });
    }
  };

  // ============================================
  // INJECT GLOBAL STYLES
  // ============================================
  const injectStyles = () => {
    const styles = `
      @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }
      
      .spin {
        animation: spin 1s linear infinite;
      }
      
      .notification-toast__close {
        background: none;
        border: none;
        color: white;
        font-size: 24px;
        cursor: pointer;
        padding: 0;
        line-height: 1;
        opacity: 0.8;
        transition: opacity 0.2s;
      }
      
      .notification-toast__close:hover {
        opacity: 1;
      }
      
      .notification-toast__icon {
        flex-shrink: 0;
      }
      
      .notification-toast__message {
        flex: 1;
      }
    `;
    
    const styleSheet = document.createElement('style');
    styleSheet.textContent = styles;
    document.head.appendChild(styleSheet);
  };

  // ============================================
  // INITIALIZE ALL MODULES
  // ============================================
  const init = () => {
    injectStyles();
    ThemeManager.init();
    RevealManager.init();
    CartManager.init();
    QuantityManager.init();
    SmoothScroll.init();
    LazyLoader.init();
    A11y.init();
    ButtonFeedback.init();
    
    // Remove no-js class
    document.documentElement.classList.remove('no-js');
    document.documentElement.classList.add('js');
    
    // Console welcome
    console.log('%c¡Bienvenido a NANO Tech Store!', 'color: #6366F1; font-size: 18px; font-weight: bold;');
    console.log('%cDiseño 2026 - Bento Grids | Neuro-diseño | Low-Carbon', 'color: #6B7280; font-size: 12px;');
  };

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
