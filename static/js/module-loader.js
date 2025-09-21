/**
 * DECTERUM Module Loader
 * Sistema de carregamento dinâmico de módulos
 */

window.DECTERUM = window.DECTERUM || {};

window.DECTERUM.ModuleLoader = (function() {
    'use strict';

    const modules = new Map();
    const loadedCSS = new Set();
    const loadedJS = new Set();

    /**
     * Carrega um módulo completo (HTML, CSS, JS)
     */
    async function loadModule(moduleName, container) {
        try {
            console.log(`📦 Loading module: ${moduleName}`);

            // Carrega CSS se ainda não foi carregado
            await loadCSS(`/static/css/modules/${moduleName}.css`);

            // Carrega JavaScript se ainda não foi carregado
            await loadJS(`/static/js/modules/${moduleName}.js`);

            // Carrega HTML e injeta no container
            await loadHTML(`/static/html/modules/${moduleName}.html`, container);

            // Inicializa o módulo se tiver função init
            let moduleObj = window.DECTERUM[capitalize(moduleName)];

            // Para módulos que não estão no namespace DECTERUM
            if (!moduleObj) {
                if (moduleName === 'videos') {
                    moduleObj = window.VideoModule;
                } else {
                    moduleObj = window[capitalize(moduleName) + 'Module'];
                }
            }

            if (moduleObj && typeof moduleObj.init === 'function') {
                moduleObj.init();
            }

            modules.set(moduleName, { loaded: true, container });
            console.log(`✅ Module ${moduleName} loaded successfully`);

        } catch (error) {
            console.error(`❌ Error loading module ${moduleName}:`, error);
            throw error;
        }
    }

    /**
     * Carrega arquivo CSS
     */
    function loadCSS(href) {
        return new Promise((resolve, reject) => {
            if (loadedCSS.has(href)) {
                resolve();
                return;
            }

            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = href;

            link.onload = () => {
                loadedCSS.add(href);
                resolve();
            };

            link.onerror = () => {
                reject(new Error(`Failed to load CSS: ${href}`));
            };

            document.head.appendChild(link);
        });
    }

    /**
     * Carrega arquivo JavaScript
     */
    function loadJS(src) {
        return new Promise((resolve, reject) => {
            if (loadedJS.has(src)) {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = src;
            script.type = 'text/javascript';

            script.onload = () => {
                loadedJS.add(src);
                resolve();
            };

            script.onerror = () => {
                reject(new Error(`Failed to load JS: ${src}`));
            };

            document.head.appendChild(script);
        });
    }

    /**
     * Carrega e injeta HTML
     */
    async function loadHTML(url, container) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const html = await response.text();

            if (typeof container === 'string') {
                container = document.getElementById(container);
            }

            if (container) {
                container.innerHTML = html;
            }

        } catch (error) {
            console.error(`Failed to load HTML from ${url}:`, error);
            throw error;
        }
    }

    /**
     * Descarrega um módulo
     */
    function unloadModule(moduleName) {
        const moduleInfo = modules.get(moduleName);
        if (moduleInfo && moduleInfo.container) {
            if (typeof moduleInfo.container === 'string') {
                const container = document.getElementById(moduleInfo.container);
                if (container) container.innerHTML = '';
            } else {
                moduleInfo.container.innerHTML = '';
            }

            modules.delete(moduleName);
            console.log(`🗑️ Module ${moduleName} unloaded`);
        }
    }

    /**
     * Verifica se um módulo está carregado
     */
    function isModuleLoaded(moduleName) {
        return modules.has(moduleName) && modules.get(moduleName).loaded;
    }

    /**
     * Lista módulos carregados
     */
    function getLoadedModules() {
        return Array.from(modules.keys());
    }

    /**
     * Capitaliza primeira letra
     */
    function capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    /**
     * Precarrega módulos críticos
     */
    async function preloadCriticalModules() {
        const criticalModules = ['feed', 'videos']; // Lista de módulos críticos

        for (const moduleName of criticalModules) {
            try {
                // Precarrega apenas CSS e JS, não o HTML
                await loadCSS(`/static/css/modules/${moduleName}.css`);
                await loadJS(`/static/js/modules/${moduleName}.js`);
                console.log(`⚡ Preloaded critical module: ${moduleName}`);
            } catch (error) {
                console.warn(`⚠️ Failed to preload critical module ${moduleName}:`, error);
            }
        }
    }

    // API pública
    return {
        loadModule,
        unloadModule,
        isModuleLoaded,
        getLoadedModules,
        preloadCriticalModules,
        loadCSS,
        loadJS,
        loadHTML
    };
})();

// Auto-inicialização
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DECTERUM Module Loader initialized');

    // Precarrega módulos críticos
    window.DECTERUM.ModuleLoader.preloadCriticalModules();
});