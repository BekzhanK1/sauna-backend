from django.core.management.base import BaseCommand
from bookings.models import Booking


class Command(BaseCommand):
    help = 'Backfill final_price for existing bookings that do not have it set'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Find bookings without final_price set
        bookings_without_price = Booking.objects.filter(final_price__isnull=True)
        
        total_count = bookings_without_price.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No bookings found without final_price set.')
            )
            return
        
        self.stdout.write(
            f'Found {total_count} bookings without final_price set.'
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No changes will be made')
            )
            
            # Show sample of what would be updated
            sample_bookings = bookings_without_price[:5]
            for booking in sample_bookings:
                calculated_price = booking.calculate_final_price()
                self.stdout.write(
                    f'Booking {booking.id}: would set final_price to {calculated_price}'
                )
            
            if total_count > 5:
                self.stdout.write(f'... and {total_count - 5} more bookings')
        else:
            # Actually update the bookings
            updated_count = 0
            for booking in bookings_without_price:
                booking.final_price = booking.calculate_final_price()
                booking.save(update_fields=['final_price'])
                updated_count += 1
                
                if updated_count % 100 == 0:
                    self.stdout.write(f'Updated {updated_count} bookings...')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated final_price for {updated_count} bookings.'
                )
            )
