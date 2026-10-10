const { Plugin, Notice, Keymap } = require("obsidian");

const HOME = "@@HOME_NOTE@@";

module.exports = class HomeButton extends Plugin {
  onload() {
    const el = this.addRibbonIcon("home", "Home", (evt) => this.goHome(Keymap.isModEvent(evt)));
    el.addClass("home-button-ribbon");

    this.addCommand({
      id: "open-home",
      name: "Open Home",
      callback: () => this.goHome(false),
    });
  }

  async goHome(newLeaf) {
    const file = this.app.metadataCache.getFirstLinkpathDest(HOME, "");
    if (!file) {
      new Notice(`Home note "${HOME}" not found`);
      return;
    }
    // Reuse a tab that already shows the hub instead of stacking copies
    if (!newLeaf) {
      const open = this.app.workspace
        .getLeavesOfType("markdown")
        .find((l) => l.view?.file?.path === file.path);
      if (open) {
        this.app.workspace.setActiveLeaf(open, { focus: true });
        return;
      }
    }
    // Always open in the main area: when a sidebar tab (Bookmarks, Search) was the last thing clicked,
    // the "current" leaf can be that sidebar tab, and opening there replaces it with the note.
    const ws = this.app.workspace;
    let leaf = newLeaf ? null : ws.getMostRecentLeaf(ws.rootSplit);
    if (!leaf || leaf.getRoot() !== ws.rootSplit || leaf.getViewState().pinned) leaf = ws.getLeaf("tab");
    await leaf.openFile(file);
    ws.setActiveLeaf(leaf, { focus: true });
  }
};
