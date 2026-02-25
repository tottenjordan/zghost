import type { Character } from './types';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';

interface CharacterGalleryProps {
  characters: Character[];
}

export function CharacterGallery({ characters }: CharacterGalleryProps) {
  if (characters.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-zinc-700 bg-zinc-900/50">
        <p className="text-zinc-500">No character reference images yet</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {characters.map((character) => (
        <Card
          key={character.id}
          className="group cursor-pointer transition-all hover:border-zinc-600"
        >
          {/* Character Image */}
          <div className="relative aspect-square w-full overflow-hidden rounded-t-lg bg-zinc-900">
            <img
              src={character.imageUrl}
              alt={character.name}
              className="h-full w-full object-cover transition-transform group-hover:scale-105"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="100" height="100"%3E%3Crect fill="%2318181b" width="100" height="100"/%3E%3C/svg%3E';
              }}
            />
          </div>

          {/* Character Info */}
          <div className="p-3">
            <h4 className="mb-1 truncate text-sm font-medium capitalize text-zinc-100">
              {character.name}
            </h4>
            <div className="flex items-center justify-between">
              <span className="text-xs text-zinc-400">
                Used {character.usageCount}x
              </span>
              <Badge variant="default" className="text-xs">
                Subject
              </Badge>
            </div>
            {character.description && (
              <p className="mt-2 line-clamp-2 text-xs text-zinc-500">
                {character.description}
              </p>
            )}
          </div>
        </Card>
      ))}
    </div>
  );
}
