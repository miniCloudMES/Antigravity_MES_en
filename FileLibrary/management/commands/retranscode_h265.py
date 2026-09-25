from django.core.management.base import BaseCommand
from FileLibrary.models import LibraryFile
from FileLibrary.video import transcode_video


class Command(BaseCommand):
    help = 'Reset completed H.265 Standardized Video to pending transcode (re-transcode using H.264)'

    def add_arguments(self, parser):
        parser.add_argument('--sync', action='store_true', help='Execute synchronously (wait until complete)')
        parser.add_argument('--list-only', action='store_true', help='List only, do not re-transcode')

    def handle(self, *args, **options):
        done = LibraryFile.objects.filter(video_status='COMPLETED', video_standard__isnull=False)

        if options['list_only']:
            self.stdout.write(f'Completed videos: {done.count()}')
            for f in done:
                self.stdout.write(f'  #{f.pk} {f.title}')
            return

        if done.count() == 0:
            self.stdout.write('No videos need re-transcoding.')
            return

        self.stdout.write(f'Resetting {done.count()} video(s) to pending transcode (H.264)...')
        for f in done:
            f.video_status = 'PENDING'
            f.video_error = ''
            f.save(update_fields=['video_status', 'video_error'])
            transcode_video(f.pk, sync=options['sync'])
            self.stdout.write(f'  #{f.pk} {f.title} -> triggered')
        self.stdout.write(self.style.SUCCESS('Completed.'))
