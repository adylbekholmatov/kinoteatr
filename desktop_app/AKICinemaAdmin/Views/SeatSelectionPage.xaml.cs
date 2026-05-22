using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using AKICinemaAdmin.Models;

namespace AKICinemaAdmin.Views;

public partial class SeatSelectionPage : Page
{
    public event Action<BookingResult, Screening>? BookingCompleted;
    public event Action? BackRequested;

    private readonly Screening _screening;
    private SeatMapResponse? _seatMap;
    private readonly List<SeatInfo> _selectedSeats = new();
    private decimal _price;

    public SeatSelectionPage(Screening screening)
    {
        InitializeComponent();
        _screening = screening;
        MovieTitleLabel.Text = screening.Movie.TitleRu;
        ScreeningInfoLabel.Text = $"{screening.StartTime}  |  {screening.Hall.Name}  |  {screening.PriceDecimal:0} сом/место";
        PriceLabel.Text = $"{screening.PriceDecimal:0} сом";
        _price = screening.PriceDecimal;
        _ = LoadSeatMapAsync();
    }

    private async System.Threading.Tasks.Task LoadSeatMapAsync()
    {
        SeatLoadingPanel.Visibility = Visibility.Visible;
        SeatScrollView.Visibility = Visibility.Collapsed;

        _seatMap = await App.Api.GetSeatMapAsync(_screening.Id);

        SeatLoadingPanel.Visibility = Visibility.Collapsed;

        if (_seatMap == null)
        {
            SeatLoadingPanel.Visibility = Visibility.Visible;
            var lbl = SeatLoadingPanel.Children.OfType<TextBlock>().LastOrDefault();
            if (lbl != null) lbl.Text = "Не удалось загрузить схему зала.";
            return;
        }

        BuildSeatMap();
        SeatScrollView.Visibility = Visibility.Visible;
    }

    private void BuildSeatMap()
    {
        SeatMapPanel.Children.Clear();
        if (_seatMap == null) return;

        var sortedRows = _seatMap.Rows.OrderBy(r => int.TryParse(r.Key, out var n) ? n : 999);

        foreach (var (rowKey, seats) in sortedRows)
        {
            var rowPanel = new StackPanel
            {
                Orientation = Orientation.Horizontal,
                HorizontalAlignment = HorizontalAlignment.Center,
                Margin = new Thickness(0, 0, 0, 6)
            };

            // Row label left
            rowPanel.Children.Add(new TextBlock
            {
                Text = rowKey,
                Width = 32,
                Foreground = new SolidColorBrush(Color.FromRgb(100, 100, 100)),
                FontSize = 14,
                FontWeight = FontWeights.SemiBold,
                VerticalAlignment = VerticalAlignment.Center,
                TextAlignment = TextAlignment.Center,
                Margin = new Thickness(0, 0, 8, 0)
            });

            foreach (var seat in seats.OrderBy(s => s.Number))
            {
                var btn = CreateSeatButton(seat);
                rowPanel.Children.Add(btn);
            }

            // Row label right
            rowPanel.Children.Add(new TextBlock
            {
                Text = rowKey,
                Width = 32,
                Foreground = new SolidColorBrush(Color.FromRgb(100, 100, 100)),
                FontSize = 14,
                FontWeight = FontWeights.SemiBold,
                VerticalAlignment = VerticalAlignment.Center,
                TextAlignment = TextAlignment.Center,
                Margin = new Thickness(8, 0, 0, 0)
            });

            SeatMapPanel.Children.Add(rowPanel);
        }
    }

    private Button CreateSeatButton(SeatInfo seat)
    {
        var btn = new Button
        {
            Width = 76,
            Height = 76,
            Margin = new Thickness(6),
            Content = seat.Number.ToString(),
            FontSize = 18,
            FontWeight = FontWeights.SemiBold,
            Tag = seat,
            Cursor = seat.IsBooked ? Cursors.No : Cursors.Hand,
            IsEnabled = !seat.IsBooked,
            ToolTip = $"Ряд {seat.Row}, Место {seat.Number}",
        };

        UpdateSeatButtonStyle(btn, seat);

        if (!seat.IsBooked)
        {
            btn.Click += SeatButton_Click;
            btn.MouseEnter += (s, e) =>
            {
                if (!seat.IsSelected)
                    ((Button)s).Background = new SolidColorBrush(Color.FromRgb(200, 16, 46));
            };
            btn.MouseLeave += (s, e) =>
            {
                if (!seat.IsSelected)
                    UpdateSeatButtonStyle((Button)s, seat);
            };
        }

        var template = new ControlTemplate(typeof(Button));
        var border = new FrameworkElementFactory(typeof(Border));
        border.SetBinding(Border.BackgroundProperty, new System.Windows.Data.Binding("Background") { RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        border.SetBinding(Border.BorderBrushProperty, new System.Windows.Data.Binding("BorderBrush") { RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        border.SetValue(Border.BorderThicknessProperty, new Thickness(1));
        border.SetValue(Border.CornerRadiusProperty, new CornerRadius(6, 6, 4, 4));

        var cp = new FrameworkElementFactory(typeof(ContentPresenter));
        cp.SetValue(ContentPresenter.HorizontalAlignmentProperty, HorizontalAlignment.Center);
        cp.SetValue(ContentPresenter.VerticalAlignmentProperty, VerticalAlignment.Center);
        border.AppendChild(cp);
        template.VisualTree = border;
        btn.Template = template;

        return btn;
    }

    private void UpdateSeatButtonStyle(Button btn, SeatInfo seat)
    {
        if (seat.IsBooked)
        {
            btn.Background = new SolidColorBrush(Color.FromRgb(34, 34, 34));
            btn.BorderBrush = new SolidColorBrush(Color.FromRgb(40, 40, 40));
            btn.Foreground = new SolidColorBrush(Color.FromRgb(60, 60, 60));
        }
        else if (seat.IsSelected)
        {
            btn.Background = new SolidColorBrush(Color.FromRgb(200, 16, 46));
            btn.BorderBrush = new SolidColorBrush(Color.FromRgb(232, 33, 62));
            btn.Foreground = new SolidColorBrush(Colors.White);
        }
        else
        {
            btn.Background = new SolidColorBrush(Color.FromRgb(42, 42, 42));
            btn.BorderBrush = new SolidColorBrush(Color.FromRgb(80, 80, 80));
            btn.Foreground = new SolidColorBrush(Color.FromRgb(170, 170, 170));
        }
    }

    private void SeatButton_Click(object sender, RoutedEventArgs e)
    {
        var btn = (Button)sender;
        var seat = (SeatInfo)btn.Tag;

        if (seat.IsSelected)
        {
            seat.IsSelected = false;
            _selectedSeats.Remove(seat);
        }
        else
        {
            seat.IsSelected = true;
            _selectedSeats.Add(seat);
        }

        UpdateSeatButtonStyle(btn, seat);
        UpdateOrderPanel();
    }

    private void UpdateOrderPanel()
    {
        NoSeatsHint.Visibility = _selectedSeats.Count == 0 ? Visibility.Visible : Visibility.Collapsed;

        // Remove old seat tags
        var toRemove = SelectedSeatsList.Children.OfType<Border>().ToList();
        foreach (var item in toRemove) SelectedSeatsList.Children.Remove(item);

        foreach (var s in _selectedSeats)
        {
            var tag = new Border
            {
                Background = new SolidColorBrush(Color.FromArgb(30, 200, 16, 46)),
                BorderBrush = new SolidColorBrush(Color.FromArgb(80, 200, 16, 46)),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(4),
                Padding = new Thickness(8, 4, 8, 4),
                Margin = new Thickness(0, 3, 0, 0)
            };

            var grid = new Grid();
            grid.Children.Add(new TextBlock
            {
                Text = $"Ряд {s.Row}, Место {s.Number}",
                Foreground = new SolidColorBrush(Color.FromRgb(240, 240, 240)),
                FontSize = 12
            });
            grid.Children.Add(new TextBlock
            {
                Text = $"{_price:0} сом",
                HorizontalAlignment = HorizontalAlignment.Right,
                Foreground = new SolidColorBrush(Color.FromRgb(200, 16, 46)),
                FontSize = 12,
                FontWeight = FontWeights.SemiBold
            });
            tag.Child = grid;
            SelectedSeatsList.Children.Add(tag);
        }

        var count = _selectedSeats.Count;
        var total = count * _price;
        SeatsCountLabel.Text = count.ToString();
        TotalLabel.Text = $"{total:0} сом";
        BookButton.IsEnabled = count > 0;
        ErrorBorder.Visibility = Visibility.Collapsed;
    }

    private async void BookButton_Click(object sender, RoutedEventArgs e)
    {
        var phone = PhoneBox.Text.Trim();
        if (string.IsNullOrEmpty(phone) || phone == "+996 ")
        {
            ShowError("Введите номер телефона клиента.");
            return;
        }

        if (_selectedSeats.Count == 0)
        {
            ShowError("Выберите места.");
            return;
        }

        BookButton.IsEnabled = false;
        BookButton.Content = "⏳ Оформление...";
        ErrorBorder.Visibility = Visibility.Collapsed;

        var seatIds = _selectedSeats.Select(s => s.Id).ToList();
        var email = EmailBox.Text.Trim();

        var (success, result, error) = await App.Api.CreateBookingAsync(
            _screening.Id, seatIds, phone, email);

        if (success && result != null)
        {
            BookingCompleted?.Invoke(result, _screening);
        }
        else
        {
            ShowError(error);
            BookButton.IsEnabled = true;
            BookButton.Content = "🎟  Оформить билет";
        }
    }

    private void ShowError(string msg)
    {
        ErrorText.Text = msg;
        ErrorBorder.Visibility = Visibility.Visible;
    }

    private void BackButton_Click(object sender, RoutedEventArgs e)
        => BackRequested?.Invoke();
}
