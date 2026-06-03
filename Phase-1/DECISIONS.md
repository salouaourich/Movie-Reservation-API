# DECISIONS.md — Movie Reservation API

## 1. Seat Locking Strategy

To stop double booking, we use Redis seat holds with a 5-minute TTL.
When a user selects a seat, Redis uses `SET NX EX` so only one user can hold the seat at a time.
If the hold expires or the user leaves checkout, the seat becomes available automatically.
When payment is confirmed, the booking is saved in PostgreSQL inside a transaction, and a unique constraint on `(showing_id, seat_id)` guarantees the same seat cannot be booked twice.

## 2. Pricing Model

Ticket prices change depending on hall occupancy.

* Less than 50% booked → normal price
* 50%–80% booked → +15%
* More than 80% booked → +25%

VIP seats also use a 1.5x multiplier.
The final price is saved in `price_at_booking` so the customer’s ticket price never changes later.

## 3. Other Design Decisions

* Tickets are stored as unique codes instead of PDF files.
* Booking cancellations use `status = 'cancelled'` instead of deleting data.
* The system supports one cinema with multiple halls.
* Redis handles temporary seat holds, while PostgreSQL stores confirmed bookings permanently.
