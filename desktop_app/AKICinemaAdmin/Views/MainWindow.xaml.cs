using System;
using System.Windows;
using System.Windows.Input;
using System.Windows.Threading;

namespace AKICinemaAdmin.Views;

public partial class MainWindow : Window
{
    // Segoe MDL2 Assets glyphs
    private const string GlyphMaximize = "\uE922";
    private const string GlyphRestore  = "\uE923";

    private readonly DispatcherTimer _pollTimer;

    public MainWindow()
    {
        InitializeComponent();
        UserLabel.Text = $"👤 {App.Api.Username}";

        MaxHeight = SystemParameters.WorkArea.Height;
        MaxWidth  = SystemParameters.WorkArea.Width;

        NavigateToSchedule();
        UpdateMaxRestoreButton();

        // Poll every 30 seconds for pending receipts
        _pollTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(30) };
        _pollTimer.Tick += async (_, _) => await RefreshPendingReceiptsAsync();
        _pollTimer.Start();

        // Initial check
        _ = RefreshPendingReceiptsAsync();
    }

    private async System.Threading.Tasks.Task RefreshPendingReceiptsAsync()
    {
        try
        {
            var receipts = await App.Api.GetPendingReceiptsAsync();
            int count = receipts.Count;
            Dispatcher.Invoke(() =>
            {
                ReceiptBadgeText.Text = count.ToString();
                ReceiptBadge.Visibility = count > 0 ? Visibility.Visible : Visibility.Collapsed;
            });
        }
        catch { }
    }

    private void Window_StateChanged(object sender, EventArgs e)
        => UpdateMaxRestoreButton();

    private void UpdateMaxRestoreButton()
    {
        if (MaxRestoreBtn == null) return;
        bool max = WindowState == WindowState.Maximized;
        MaxRestoreBtn.Content = max ? GlyphRestore : GlyphMaximize;
        MaxRestoreBtn.ToolTip = max ? "Восстановить" : "Развернуть";
    }

    private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount == 2) { ToggleMaximize(); return; }
        if (WindowState == WindowState.Maximized)
        {
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
        _pollTimer.Stop();
        App.Api.Logout();
        var login = new LoginView();
        login.Show();
        Close();
    }

    private void BtnSchedule_Click(object sender, RoutedEventArgs e)
        => NavigateToSchedule();

    private void BtnSearch_Click(object sender, RoutedEventArgs e)
        => ContentFrame.Navigate(new SearchView());

    private void BtnScan_Click(object sender, RoutedEventArgs e)
        => ContentFrame.Navigate(new ScanTicketPage());

    private void BtnReceipts_Click(object sender, RoutedEventArgs e)
    {
        var page = new ReceiptsPage();
        page.ReceiptsRefreshed += async () => await RefreshPendingReceiptsAsync();
        ContentFrame.Navigate(page);
    }

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
