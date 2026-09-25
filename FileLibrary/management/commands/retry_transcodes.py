from django.core.management.base import BaseCommand
from FileLibrary.models import LibraryFile
from FileLibrary.video import transcode_video
from django.db.models import Q


class Command(BaseCommand):
    help = 'Scan incomplete transcode videos and re-trigger transcoding (for cron)'

    def add_arguments(self, parser):
        parser.add_argument('--sync', action='store_true', help='Execute synchronously (suitable for cron)')
        parser.add_argument('--list-only', action='store_true', help='List incomplete videos only, do not transcode')

    def handle(self, *args, **options):
        video_expr = Q()
        for ext in LibraryFile.VIDEO_EXTS:
            video_expr |= Q(file__endswith='.' + ext)
        pending = LibraryFile.objects.filter(video_expr).exclude(video_status='COMPLETED')

        if options['list_only']:
            self.stdout.write(f'Incomplete transcode videos: {pending.count()}')
            for f in pending:
                self.stdout.write(f'  #{f.pk} {f.title} | {f.video_status} | {f.created_at:%Y-%m-%d %H:%M}')
            return

        if pending.count() == 0:
            self.stdout.write('No videos need re-transcoding.')
            return

        self.stdout.write(f'Restarting transcoding for {pending.count()} video(s)...')
        for f in pending:
            f.video_status = 'PENDING'
            f.video_error = ''
            f.save(update_fields=['video_status', 'video_error'])
            transcode_video(f.pk, sync=options['sync'])
            self.stdout.write(f'  #{f.pk} {f.title} -> triggered')
        self.stdout.write(self.style.SUCCESS('Completed.'))
