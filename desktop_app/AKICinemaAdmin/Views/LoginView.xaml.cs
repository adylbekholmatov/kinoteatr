using System.Windows;
using System.Windows.Input;

namespace AKICinemaAdmin.Views;

public partial class LoginView : Window
{
    public LoginView()
    {
        InitializeComponent();
        UsernameBox.Focus();
    }

    private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        => DragMove();

    private void CloseButton_Click(object sender, RoutedEventArgs e)
        => Application.Current.Shutdown();

    private void Input_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter) LoginButton_Click(sender, e);
    }

    private async void LoginButton_Click(object sender, RoutedEventArgs e)
    {
        var url      = ServerUrlBox.Text.Trim();
        var username = UsernameBox.Text.Trim();
        var password = PasswordBox.Password;

        if (string.IsNullOrEmpty(username) || string.IsNullOrEmpty(password))
        {
            ShowError("Введите логин и пароль.");
            return;
        }

        LoginButton.IsEnabled = false;
        LoginButton.Content   = "Подключение...";
        ErrorBorder.Visibility = Visibility.Collapsed;

        App.Api.BaseUrl = url;
        var (success, message) = await App.Api.LoginAsync(username, password);

        if (success)
        {
            var main = new MainWindow();
            main.Show();
            Close();
        }
        else
        {
            ShowError(message);
            LoginButton.IsEnabled = true;
            LoginButton.Content   = "Войти в систему";
        }
    }

    private void ShowError(string msg)
    {
        ErrorText.Text = msg;
        ErrorBorder.Visibility = Visibility.Visible;
    }
}
