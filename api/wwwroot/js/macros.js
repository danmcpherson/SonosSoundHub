/**
 * Macro Management Module
 */
window.macros = {
    currentMacros: [],
    editingMacro: null,

    /**
     * Loads all macros
     */
    async load() {
        const list = document.getElementById('macros-list');
        list.innerHTML = '<div class="loading-message"><div class="spinner"></div><p>Loading macros...</p></div>';

        try {
            const macroList = await api.getMacros();
            this.currentMacros = macroList;

            if (macroList.length === 0) {
                list.innerHTML = `
                    <div class="info-message">
                        <p>No macros yet. Create your first macro to automate your Sonos system!</p>
                    </div>
                `;
                return;
            }

            list.innerHTML = '';
            macroList.forEach(macro => {
                const card = createMacroCard(macro);
                list.appendChild(card);
            });
        } catch (error) {
            console.error('Failed to load macros:', error);
            list.innerHTML = `
                <div class="info-message">
                    <p>Error loading macros: ${error.message}</p>
                </div>
            `;
        }
    },

    /**
     * Opens the macro editor for creating a new macro
     */
    create() {
        this.editingMacro = null;
        document.getElementById('modal-title').textContent = 'Create Macro';
        document.getElementById('macro-name').value = '';
        document.getElementById('macro-description').value = '';
        document.getElementById('macro-category').value = '';
        document.getElementById('macro-definition').value = '';
        document.getElementById('macro-name').disabled = false;
        toggleMacroModal(true);
    },

    /**
     * Opens the macro editor for editing an existing macro
     */
    async edit(macroName) {
        try {
            const macro = await api.getMacro(macroName);
            this.editingMacro = macro;

            document.getElementById('modal-title').textContent = 'Edit Macro';
            document.getElementById('macro-name').value = macro.name;
            document.getElementById('macro-description').value = macro.description || '';
            document.getElementById('macro-category').value = macro.category || '';
            document.getElementById('macro-definition').value = macro.definition;
            document.getElementById('macro-name').disabled = true;

            toggleMacroModal(true);
        } catch (error) {
            showToast('Failed to load macro', 'error');
        }
    },

    /**
     * Saves a macro (create or update)
     */
    async save(event) {
        event.preventDefault();

        const name = document.getElementById('macro-name').value.trim();
        const description = document.getElementById('macro-description').value.trim();
        const category = document.getElementById('macro-category').value.trim();
        const definition = document.getElementById('macro-definition').value.trim();

        if (!name || !definition) {
            showToast('Name and definition are required', 'warning');
            return;
        }

        // Validate macro name
        if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
            showToast('Macro name can only contain letters, numbers, underscores, and dashes', 'warning');
            return;
        }

        const macro = {
            name,
            description: description || null,
            category: category || null,
            definition,
            isFavorite: this.editingMacro?.isFavorite || false,
            parameters: this.detectParameters(definition)
        };

        try {
            await api.saveMacro(macro);
            showToast(`Macro '${name}' saved successfully`, 'success');
            toggleMacroModal(false);
            await this.load();
        } catch (error) {
            showToast('Failed to save macro: ' + error.message, 'error');
        }
    },

    /**
     * Deletes a macro
     */
    async delete(macroName) {
        if (!confirm(`Are you sure you want to delete the macro '${macroName}'?`)) {
            return;
        }

        try {
            await api.deleteMacro(macroName);
            showToast(`Macro '${macroName}' deleted`, 'success');
            await this.load();
        } catch (error) {
            showToast('Failed to delete macro', 'error');
        }
    },

    /**
     * Executes a macro
     */
    async execute(macroName, args = []) {
        try {
            // If macro has parameters, prompt for them
            const macro = this.currentMacros.find(m => m.name === macroName);
            if (macro && macro.parameters && macro.parameters.length > 0 && args.length === 0) {
                // For now, we'll execute without args - future enhancement: parameter input dialog
                showToast('Parameter input coming soon. Executing with defaults...', 'warning');
            }

            showToast(`Executing macro '${macroName}'...`, 'success');
            const result = await api.executeMacro(macroName, args);
            
            console.log('Macro execution result:', result);
            showToast(`Macro '${macroName}' executed successfully`, 'success');
        } catch (error) {
            showToast(`Failed to execute macro: ${error.message}`, 'error');
        }
    },

    /**
     * Detects parameters (%1-%12) in a macro definition
     */
    detectParameters(definition) {
        const params = [];
        const regex = /%(\d+)/g;
        let match;

        while ((match = regex.exec(definition)) !== null) {
            const position = parseInt(match[1]);
            if (!params.find(p => p.position === position)) {
                params.push({
                    position,
                    name: `Parameter ${position}`,
                    description: null,
                    type: 'string',
                    defaultValue: null
                });
            }
        }

        return params.sort((a, b) => a.position - b.position);
    }
};
