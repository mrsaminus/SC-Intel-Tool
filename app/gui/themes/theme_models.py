from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    category: str
    description: str
    colors: dict
    metrics: dict
    notes: str = ""

    def with_updates(self, key, name, category=None, description=None, colors=None, metrics=None, notes=None):
        updated_colors = dict(self.colors)
        if colors:
            updated_colors.update(colors)
        updated_metrics = dict(self.metrics)
        if metrics:
            updated_metrics.update(metrics)
        return replace(
            self,
            key=key,
            name=name,
            category=category or self.category,
            description=description or self.description,
            colors=updated_colors,
            metrics=updated_metrics,
            notes=self.notes if notes is None else notes,
        )
