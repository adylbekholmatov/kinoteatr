using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using Newtonsoft.Json;

namespace AKICinemaAdmin.Models;

public class Genre
{
    [JsonProperty("id")]        public int Id { get; set; }
    [JsonProperty("name_ru")]   public string NameRu { get; set; } = "";
}

public class Movie
{
    [JsonProperty("id")]          public int Id { get; set; }
    [JsonProperty("title_ru")]    public string TitleRu { get; set; } = "";
    [JsonProperty("title_ky")]    public string TitleKy { get; set; } = "";
    [JsonProperty("duration")]    public int Duration { get; set; }
    [JsonProperty("age_rating")]  public string AgeRating { get; set; } = "";
    [JsonProperty("poster_url")]  public string? PosterUrl { get; set; }

    public string DurationDisplay => Duration >= 60
        ? $"{Duration / 60} ч {Duration % 60} мин"
        : $"{Duration} мин";
}

public class Hall
{
    [JsonProperty("id")]          public int Id { get; set; }
    [JsonProperty("name")]        public string Name { get; set; } = "";
    [JsonProperty("hall_type")]   public string HallType { get; set; } = "regular";
    [JsonProperty("total_seats")] public int TotalSeats { get; set; }

    public bool IsVip => HallType == "vip";
    public string TypeLabel => IsVip ? "VIP" : "Стандарт";
}

public class Screening
{
    [JsonProperty("id")]               public int Id { get; set; }
    [JsonProperty("movie")]            public Movie Movie { get; set; } = new();
    [JsonProperty("hall")]             public Hall Hall { get; set; } = new();
    [JsonProperty("start_time")]       public string StartTime { get; set; } = "";
    [JsonProperty("price")]            public string Price { get; set; } = "0";
    [JsonProperty("available_seats")]  public int AvailableSeats { get; set; }

    public string TimeDisplay  => StartTime.Length >= 16 ? StartTime.Substring(11, 5) : StartTime;
    public string DateDisplay  => StartTime.Length >= 10 ? StartTime.Substring(0, 10) : StartTime;
    public decimal PriceDecimal => decimal.TryParse(Price, System.Globalization.NumberStyles.Any,
        System.Globalization.CultureInfo.InvariantCulture, out var p) ? p : 0;
}

public class SeatInfo : INotifyPropertyChanged
{
    [JsonProperty("id")]        public int Id { get; set; }
    [JsonProperty("row")]       public int Row { get; set; }
    [JsonProperty("number")]    public int Number { get; set; }
    [JsonProperty("is_booked")] public bool IsBooked { get; set; }

    private bool _isSelected;
    public bool IsSelected
    {
        get => _isSelected;
        set { _isSelected = value; OnPropertyChanged(); OnPropertyChanged(nameof(State)); }
    }

    public string State => IsBooked ? "booked" : IsSelected ? "selected" : "free";
    public string Label => $"Р{Row} М{Number}";

    public event PropertyChangedEventHandler? PropertyChanged;
    protected void OnPropertyChanged([CallerMemberName] string? name = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

public class SeatMapResponse
{
    [JsonProperty("screening_id")] public int ScreeningId { get; set; }
    [JsonProperty("movie")]        public string Movie { get; set; } = "";
    [JsonProperty("hall")]         public string Hall { get; set; } = "";
    [JsonProperty("hall_type")]    public string HallType { get; set; } = "";
    [JsonProperty("start_time")]   public string StartTime { get; set; } = "";
    [JsonProperty("price")]        public string Price { get; set; } = "0";
    [JsonProperty("rows")]         public Dictionary<string, List<SeatInfo>> Rows { get; set; } = new();

    public decimal PriceDecimal => decimal.TryParse(Price, System.Globalization.NumberStyles.Any,
        System.Globalization.CultureInfo.InvariantCulture, out var p) ? p : 0;
}

public class BookingResult
{
    [JsonProperty("booking_code")]  public string BookingCode { get; set; } = "";
    [JsonProperty("total_amount")]  public string TotalAmount { get; set; } = "";
    [JsonProperty("seats_count")]   public int SeatsCount { get; set; }
    [JsonProperty("status")]        public string Status { get; set; } = "";
}

public class BookingDetail
{
    [JsonProperty("booking_code")]  public string BookingCode { get; set; } = "";
    [JsonProperty("movie")]         public string Movie { get; set; } = "";
    [JsonProperty("hall")]          public string Hall { get; set; } = "";
    [JsonProperty("start_time")]    public string StartTime { get; set; } = "";
    [JsonProperty("email")]         public string Email { get; set; } = "";
    [JsonProperty("phone")]         public string Phone { get; set; } = "";
    [JsonProperty("total_amount")]  public string TotalAmount { get; set; } = "";
    [JsonProperty("status")]        public string Status { get; set; } = "";
    [JsonProperty("seats")]         public List<SeatShort> Seats { get; set; } = new();
    [JsonProperty("created_at")]    public string CreatedAt { get; set; } = "";
}

public class SeatShort
{
    [JsonProperty("row")]    public int Row { get; set; }
    [JsonProperty("number")] public int Number { get; set; }
    public string Label => $"Р{Row} М{Number}";
}

public class TicketVerifyResult
{
    [JsonProperty("valid")]           public bool Valid { get; set; }
    [JsonProperty("reason")]          public string Reason { get; set; } = "";
    [JsonProperty("already_used")]    public bool AlreadyUsed { get; set; }
    [JsonProperty("manual_entry")]    public bool ManualEntry { get; set; }
    [JsonProperty("booking_code")]    public string BookingCode { get; set; } = "";
    [JsonProperty("movie")]           public string Movie { get; set; } = "";
    [JsonProperty("screening_time")]  public string ScreeningTime { get; set; } = "";
    [JsonProperty("hall")]            public string Hall { get; set; } = "";
    [JsonProperty("seats")]           public List<string> Seats { get; set; } = new();
    [JsonProperty("seats_count")]     public int SeatsCount { get; set; }
    [JsonProperty("total_amount")]    public string TotalAmount { get; set; } = "";
    [JsonProperty("phone")]           public string Phone { get; set; } = "";
    [JsonProperty("checked_in_at")]   public string CheckedInAt { get; set; } = "";
}

public class PendingReceipt
{
    [JsonProperty("id")]              public int Id { get; set; }
    [JsonProperty("booking_code")]    public string BookingCode { get; set; } = "";
    [JsonProperty("movie")]           public string Movie { get; set; } = "";
    [JsonProperty("screening_time")]  public string ScreeningTime { get; set; } = "";
    [JsonProperty("hall")]            public string Hall { get; set; } = "";
    [JsonProperty("total_amount")]    public string TotalAmount { get; set; } = "";
    [JsonProperty("email")]           public string Email { get; set; } = "";
    [JsonProperty("phone")]           public string Phone { get; set; } = "";
    [JsonProperty("receipt_url")]     public string ReceiptUrl { get; set; } = "";
    [JsonProperty("created_at")]      public string CreatedAt { get; set; } = "";
    [JsonProperty("alert_type")]      public string AlertType { get; set; } = "pending";

    public bool IsCancelledByClient => AlertType == "cancelled_by_client";
    public string StatusLabel => IsCancelledByClient ? "❌ Клиент отменил" : "⏳ Ожидает подтверждения";
}
