using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using AKICinemaAdmin.Models;

namespace AKICinemaAdmin.Views;

public partial class BookingSuccessPage : Page
{
    public event Action? NewBookingRequested;

    private readonly BookingResult _result;
    private readonly Screening _screening;

    public BookingSuccessPage(BookingResult result, Screening screening)
    {
        InitializeComponent();
        _result = result;
        _screening = screening;
        PopulateTicket();
    }

    private void PopulateTicket()
    {
        BookingCodeLabel.Text   = _result.BookingCode;
        SubtitleText.Text       = $"Код бронирования: {_result.BookingCode}";
        TicketMovieLabel.Text   = _screening.Movie.TitleRu;
        TicketHallLabel.Text    = _screening.Hall.Name;
        TicketSeatsCountLabel.Text = $"{_result.SeatsCount} шт.";
        TicketTotalLabel.Text   = $"{decimal.Parse(_result.TotalAmount, System.Globalization.CultureInfo.InvariantCulture):0} сом";

        if (_screening.StartTime.Length >= 16)
        {
            TicketDateLabel.Text = _screening.StartTime.Substring(0, 10).Replace("-", ".");
            TicketTimeLabel.Text = _screening.StartTime.Substring(11, 5);
        }

        // Load seat details async
        _ = LoadSeatsAsync();
    }

    private async System.Threading.Tasks.Task LoadSeatsAsync()
    {
        var detail = await App.Api.GetBookingDetailAsync(_result.BookingCode);
        if (detail == null) return;

        SeatsWrapPanel.Children.Clear();
        foreach (var seat in detail.Seats)
        {
            var badge = new Border
            {
                Background = new SolidColorBrush(Color.FromRgb(200, 16, 46)),
                CornerRadius = new CornerRadius(4),
                Padding = new Thickness(8, 4, 8, 4),
                Margin = new Thickness(0, 0, 6, 6)
            };
            badge.Child = new TextBlock
            {
                Text = seat.Label,
                Foreground = new SolidColorBrush(Colors.White),
                FontSize = 12,
                FontWeight = FontWeights.SemiBold
            };
            SeatsWrapPanel.Children.Add(badge);
        }
    }

    private void PrintButton_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new PrintDialog();
        if (dialog.ShowDialog() == true)
        {
            var doc = new FlowDocument();
            doc.PagePadding = new Thickness(40);
            doc.ColumnWidth = double.MaxValue;

            void AddLine(string text, double size = 14, bool bold = false, string color = "#FFFFFF")
            {
                var para = new Paragraph(new Run(text))
                {
                    FontSize = size,
                    FontWeight = bold ? FontWeights.Bold : FontWeights.Normal,
                    Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString(color)),
                    Margin = new Thickness(0, 2, 0, 2)
                };
                doc.Blocks.Add(para);
            }

            doc.Background = new SolidColorBrush(Colors.White);
            AddLine("AKI CINEMA — БИЛЕТ", 22, true, "#C8102E");
            AddLine("─────────────────────────────────", 10, false, "#999999");
            AddLine($"Код: {_result.BookingCode}", 14, true, "#000000");
            AddLine($"Фильм: {_screening.Movie.TitleRu}", 14, false, "#000000");
            AddLine($"Дата/время: {_screening.StartTime}", 13, false, "#000000");
            AddLine($"Зал: {_screening.Hall.Name}", 13, false, "#000000");
            AddLine($"Мест: {_result.SeatsCount}", 13, false, "#000000");
            AddLine("─────────────────────────────────", 10, false, "#999999");
            AddLine($"ИТОГО: {_result.TotalAmount} сом", 18, true, "#C8102E");
            AddLine("─────────────────────────────────", 10, false, "#999999");
            AddLine("Статус: Зарезервировано (касса)", 12, false, "#555555");
            AddLine("© 2026 AKI Cinema", 10, false, "#999999");

            var viewer = new FlowDocumentReader { Document = doc };
            dialog.PrintDocument(
                ((IDocumentPaginatorSource)doc).DocumentPaginator,
                "AKI Cinema — Билет");
        }
    }

    private void NewBookingButton_Click(object sender, RoutedEventArgs e)
        => NewBookingRequested?.Invoke();
}
