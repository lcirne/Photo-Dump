from django.core.management.base import BaseCommand

from api.models import Photo
from api.tasks import process_photo_upload


class Command(BaseCommand):
    help = "Requeue photos that are still marked as processing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run processing in this process instead of sending Celery tasks.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum number of processing photos to requeue.",
        )

    def handle(self, *args, **options):
        queryset = Photo.objects.filter(upload_status=Photo.UploadStatus.PROCESSING).order_by("id")
        photo_ids = list(queryset.values_list("id", flat=True)[: options["limit"]])

        if not photo_ids:
            self.stdout.write(self.style.SUCCESS("No processing photos found."))
            return

        for photo_id in photo_ids:
            if options["sync"]:
                process_photo_upload(photo_id)
            else:
                process_photo_upload.delay(photo_id)

        action = "Processed" if options["sync"] else "Requeued"
        self.stdout.write(self.style.SUCCESS(f"{action} {len(photo_ids)} photo(s): {photo_ids}"))
