using System;
using System.Windows;
using System.Windows.Input;

namespace AKICinemaAdmin.Views;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        UserLabel.Text = $"👤 {App.Api.Username}";

        // Prevent window from covering taskbar when maximized with WindowStyle=None
        MaxHeight = SystemParameters.WorkArea.Height;
        MaxWidth  = SystemParameters.WorkArea.Width;

        NavigateToSchedule();
        UpdateMaxRestoreButton();
    }

    private void Window_StateChanged(object sender, EventArgs e)
        => UpdateMaxRestoreButton();

    private void UpdateMaxRestoreButton()
    {
        if (MaxRestoreBtn == null) return;
        MaxRestoreBtn.Content = WindowState == WindowState.Maximized ? "❐" : "□";
        MaxRestoreBtn.ToolTip  = WindowState == WindowState.Maximized ? "Восстановить" : "Развернуть";
    }

    private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount == 2)
        {
            ToggleMaximize();
            return;
        }
        if (WindowState == WindowState.Maximized)
        {
            // Allow dragging from maximized state
            WindowState = WindowState.Normal;
            Left = Mouse.GetPosition(this).X - Width / 2;
            Top  = 0;
        }
        DragMove();
    }

    private void MinimizeButton_Click(object sender, RoutedEventArgs e)
        => WindowState = WindowState.Minimized;

    private void MaxRestoreButton_Click(object sender, RoutedEventArgs e)
        => ToggleMaximize();

    private void ToggleMaximize()
    {
        WindowState = WindowState == WindowState.Maximized
            ? WindowState.Normal
            : WindowState.Maximized;
    }

    private void CloseButton_Click(object sender, RoutedEventArgs e)
        => Application.Current.Shutdown();

    private void LogoutButton_Click(object sender, RoutedEventArgs e)
    {
        App.Api.Logout();
        var login = new LoginView();
        login.Show();
        Close();
    }

    private void BtnSchedule_Click(object sender, RoutedEventArgs e)
        => NavigateToSchedule();

    private void BtnSearch_Click(object sender, RoutedEventArgs e)
        => ContentFrame.Navigate(new SearchView());

    public void NavigateToSchedule()
    {
        var page = new SchedulePage();
        page.ScreeningSelected += OnScreeningSelected;
        page.ScreeningsLoaded += (date, count) =>
        {
            bool isToday = date.Date == DateTime.Today;
            TodayDateLabel.Text = isToday
                ? date.ToString("dd MMMM yyyy", new System.Globalization.CultureInfo("ru-RU")) + " (сегодня)"
                : date.ToString("dd MMMM yyyy", new System.Globalization.CultureInfo("ru-RU"));
            TodayScreeningsLabel.Text = $"{count} сеансов";
        };
        ContentFrame.Navigate(page);
    }

    private void OnScreeningSelected(Models.Screening screening)
    {
        var page = new SeatSelectionPage(screening);
        page.BookingCompleted += OnBookingCompleted;
        page.BackRequested    += NavigateToSchedule;
        ContentFrame.Navigate(page);
    }

    private void OnBookingCompleted(Models.BookingResult result, Models.Screening screening)
    {
        var page = new BookingSuccessPage(result, screening);
        page.NewBookingRequested += NavigateToSchedule;
        ContentFrame.Navigate(page);
    }
}
