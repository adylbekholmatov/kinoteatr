using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace AKICinemaAdmin.Views;

public partial class SearchView : Page
{
    public SearchView() => InitializeComponent();

    private void SearchBox_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter) SearchButton_Click(sender, e);
    }

    private async void SearchButton_Click(object sender, RoutedEventArgs e)
    {
        var code = SearchBox.Text.Trim();
        if (string.IsNullOrEmpty(code)) return;

        ResultPanel.Visibility = Visibility.Collapsed;
        ErrorPanel.Visibility  = Visibility.Collapsed;

        var detail = await App.Api.GetBookingDetailAsync(code);

        if (detail == null)
        {
            ErrorText.Text = $"Бронирование «{code}» не найдено.";
            ErrorPanel.Visibility = Visibility.Visible;
            return;
        }

        BookingCodeDisplay.Text = detail.BookingCode;
        ResultMovie.Text = detail.Movie;
        ResultTime.Text  = detail.StartTime;
        ResultHall.Text  = detail.Hall;
        ResultPhone.Text = detail.Phone;
        ResultTotal.Text = $"{detail.TotalAmount} сом";

        ResultSeats.Children.Clear();
        foreach (var seat in detail.Seats)
        {
            var badge = new Border
            {
                Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(200, 16, 46)),
                CornerRadius = new CornerRadius(4),
                Padding = new Thickness(6, 3, 6, 3),
                Margin = new Thickness(0, 0, 4, 4)
            };
            badge.Child = new TextBlock
            {
                Text = seat.Label,
                Foreground = new SolidColorBrush(Colors.White),
                FontSize = 11
            };
            ResultSeats.Children.Add(badge);
        }

        ResultPanel.Visibility = Visibility.Visible;
    }
}
